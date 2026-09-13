from odoo.tests import tagged

from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments


@tagged('post_install', '-at_install')
class TestDocumentsProjectGcClearBin(TransactionCaseDocuments):
    """Folders linked to a project must survive the documents trash
    autovacuum. Removing one would null `project.documents_folder_id`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param(
            'documents.deletion_delay', '0',
        )
        cls.Document = cls.env['documents.document']
        cls.Project = cls.env['project.project']

    def _make_project_with_folder(self, project_name):
        folder = self.Document.create({
            'type': 'folder',
            'name': f'folder for {project_name}',
            'owner_id': self.doc_user.id,
        })
        project = self.Project.create({
            'name': project_name,
            'documents_folder_id': folder.id,
        })
        return project, folder

    def test_gc_keeps_folder_of_active_project_when_folder_archived(self):
        project, folder = self._make_project_with_folder('active project')
        folder.action_archive()
        self.assertFalse(folder.active)
        self.assertTrue(project.active)

        self.Document._gc_clear_bin()

        self.assertTrue(
            folder.exists(),
            "A folder linked to an active project must survive the GC bin.",
        )
        self.assertEqual(
            project.documents_folder_id, folder,
            "The project documents_folder_id link must remain intact.",
        )

    def test_gc_keeps_folder_when_project_also_archived(self):
        project, folder = self._make_project_with_folder('archived project')
        project.action_archive()
        folder.action_archive()
        self.assertFalse(project.active)
        self.assertFalse(folder.active)

        self.Document._gc_clear_bin()

        self.assertTrue(folder.exists())
        self.assertEqual(project.documents_folder_id, folder)
