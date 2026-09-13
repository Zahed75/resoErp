# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAIEmbeddingBatching(TransactionCase):
    def _create_embedding(self, content):
        attachment = self.env["ir.attachment"].create({
            "name": f"test-{len(content)}.txt",
            "raw": b"raw",
        })
        return self.env["ai.embedding"].create({
            "attachment_id": attachment.id,
            "content": content,
            "embedding_model": "text-embedding-3-small",
        })

    def test_batches_respect_max_batch_size(self):
        """Ensure batches never exceed the configured max size."""
        embeddings = [self._create_embedding("short content") for _ in range(5)]

        with patch(
            "odoo.addons.ai.models.ai_embedding.get_embedding_config",
            return_value={"max_batch_size": 10, "max_tokens_per_request": 6},
        ):
            batches = self.env["ai.embedding"]._create_batches(embeddings, "openai")

        self.assertEqual([len(batch) for batch in batches], [2, 2, 1])

    def test_batches_split_on_token_limit(self):
        """Ensure token budget splits batches even when size allows more records."""
        embeddings = [
            self._create_embedding("a" * 8),
            self._create_embedding("b" * 12),
            self._create_embedding("c" * 12),
            self._create_embedding("d" * 4),
        ]

        with patch(
            "odoo.addons.ai.models.ai_embedding.get_embedding_config",
            return_value={"max_batch_size": 10, "max_tokens_per_request": 6},
        ):
            batches = self.env["ai.embedding"]._create_batches(embeddings, "openai")

        self.assertEqual([len(batch) for batch in batches], [2, 2])
        for batch in batches:
            token_count = sum(self.env["ai.embedding"]._estimate_tokens(emb.content) for emb in batch)
            self.assertLessEqual(token_count, 6)

    def test_recompute_only_reprocesses_sources_on_deprecated_provider(self):
        """A source on a still-valid provider must not be affected by another
        provider's deprecated embedding, even if they share the same checksum."""

        openai_agent = self.env["ai.agent"].create({
            "name": "OpenAI Agent",
            "llm_model": "gpt-4o",
        })
        google_agent = self.env["ai.agent"].create({
            "name": "Google Agent",
            "llm_model": "gemini-2.5-flash",
        })
        attachment = self.env["ir.attachment"].create({
            "name": "shared.txt",
            "raw": b"shared content",
        })

        openai_source = self.env["ai.agent.source"].create({
            "name": f"Source {openai_agent.name}",
            "agent_id": openai_agent.id,
            "type": "binary",
            "attachment_id": attachment.id,
            "status": "indexed",
            "is_active": True,
        })
        google_source = self.env["ai.agent.source"].create({
            "name": f"Source {google_agent.name}",
            "agent_id": google_agent.id,
            "type": "binary",
            "attachment_id": attachment.id,
            "status": "indexed",
            "is_active": True,
        })
        openai_embedding = self.env["ai.embedding"].create({
            "attachment_id": attachment.id,
            "content": "chunk content",
            "embedding_model": "text-embedding-3-small",
            "embedding_vector": [0.1] * 1536,
        })
        google_embedding = self.env["ai.embedding"].create({
            "attachment_id": attachment.id,
            "content": "chunk content",
            "embedding_model": "gemini-embedding-2",
            "embedding_vector": [0.1] * 1536,
        })

        with patch(
            "odoo.addons.ai.models.ai_embedding.EMBEDDING_MODELS_SELECTION",
            [("text-embedding-3-small", "OpenAI")],  # Assume that google embedding model has been deprecated
        ), patch(
            "odoo.addons.base.models.ir_cron.IrCron._trigger", autospec=True,
        ) as mock_trigger:
            self.env["ai.embedding"]._cron_remove_deprecated_models_embeddings_and_recompute()

        self.assertFalse(google_embedding.exists(), "Deprecated embedding must be removed")
        self.assertTrue(openai_embedding.exists(), "Still-valid embedding must be kept")

        self.assertEqual(google_source.status, "processing")
        self.assertFalse(google_source.is_active)
        self.assertEqual(
            openai_source.status, "indexed",
            "Source on a still-valid provider must not be reprocessed",
        )
        self.assertTrue(openai_source.is_active)
        mock_trigger.assert_called_once()
        triggered_cron = mock_trigger.call_args.args[0]
        self.assertEqual(triggered_cron, self.env.ref("ai.ir_cron_generate_embedding"))
