# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged
from odoo import Command, fields


@tagged('post_install', '-at_install')
class TestPosPreparationDisplay(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

    def test_load_preparation_display_model(self):

        config1 = self.env['pos.config'].create({
            'name': 'rest1',
            'active': False
        })
        config2 = self.env['pos.config'].create({
            'name': 'rest2'
        })
        config3 = self.env['pos.config'].create({
            'name': 'rest3'
        })
        config4 = self.env['pos.config'].create({
            'name': 'rest4'
        })

        # pos preperation display linked to specific configs
        display1 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 1',
            'pos_config_ids': [Command.link(config1.id)]
        })
        display2 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 2',
            'pos_config_ids': [Command.link(config2.id)]
        })
        display3 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 3',
            'pos_config_ids': []
        })
        display4 = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 4',
            'pos_config_ids': [Command.link(config3.id)]
        })

        config2.open_ui()
        config3.open_ui()
        config4.open_ui()

        self.assertEqual({d['id'] for d in config2.current_session_id.load_data([])['pos.prep.display']},
                         {display1.id, display2.id, display3.id})
        self.assertEqual({d['id'] for d in config3.current_session_id.load_data([])['pos.prep.display']},
                         {display1.id, display3.id, display4.id})
        self.assertEqual({d['id'] for d in config4.current_session_id.load_data([])['pos.prep.display']},
                         {display1.id, display3.id})

    def test_preparation_updated_on_stage_change(self):
        prep_display = self.env['pos.prep.display'].create({
            'name': 'Preparation Display 1',
            'pos_config_ids': [Command.link(self.config.id)],
        })
        first_stage, second_stage, final_stage = prep_display.stage_ids

        self.open_new_session()
        order = next(iter(self._create_orders([{'pos_order_lines_ui_args': [(self.product, 1)]}]).values()))
        order_line = order.lines[0]
        # Simulate sending the order to preparation
        self.env['pos.prep.order'].process_order(order.id)

        prep_line = self.env['pos.prep.line'].search([('pos_order_line_id', '=', order_line.id)])
        prep_state = self.env['pos.prep.state'].search([('prep_line_id', '=', prep_line.id)])
        self.assertEqual(prep_state.stage_id, first_stage)
        self.assertEqual(order_line.preparation_time, -1)
        self.assertEqual(order_line.service_time, -1)
        # Move order from first -> second stage
        prep_state.change_state_stage(
            {str(prep_state.id): second_stage.id},
            prep_display.id,
        )
        self.assertEqual(prep_state.stage_id, second_stage)
        self.assertNotEqual(order_line.preparation_time, -1)
        self.assertEqual(order_line.service_time, -1)
        # Move order from second -> final stage
        prep_state.change_state_stage(
            {str(prep_state.id): final_stage.id},
            prep_display.id,
        )
        self.assertEqual(prep_state.stage_id, final_stage)
        self.assertNotEqual(order_line.service_time, -1)

    def _send_order_to_display(self, prep_display):
        """Open a session, sync one order routed to prep_display, return its pos.prep.order."""
        self.open_new_session()
        order = next(iter(self._create_orders([{'pos_order_lines_ui_args': [(self.product, 1)]}]).values()))
        self.env['pos.prep.order'].process_order(order.id)
        prep_line = self.env['pos.prep.line'].search([('pos_order_line_id', '=', order.lines[0].id)])
        return prep_line.prep_order_id

    def _screen_order_count(self, prep_display):
        return len(prep_display.get_preparation_display_order(False)['pos.prep.order'])

    def _badge_order_count(self, prep_display):
        # order_count does not depend on the order records, invalidate manually
        prep_display.invalidate_recordset(['order_count'])
        return prep_display.order_count

    def test_order_count_includes_orders_older_than_today(self):
        """An order that crossed midnight while still open must stay counted in
        the kanban badge for as long as the preparation screen shows it."""
        prep_display = self.env['pos.prep.display'].create({
            'name': 'Kitchen Display',
            'pos_config_ids': [Command.link(self.config.id)],
        })
        prep_order = self._send_order_to_display(prep_display)

        self.assertEqual(self._screen_order_count(prep_display), 1)
        self.assertEqual(self._badge_order_count(prep_display), 1)

        # the session stays open past midnight
        self.env.cr.execute(
            "UPDATE pos_prep_order SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=1), prep_order.id),
        )
        prep_order.invalidate_recordset(['create_date'])

        self.assertEqual(self._screen_order_count(prep_display), 1,
                         "the order is still displayed on the preparation screen")
        self.assertEqual(self._badge_order_count(prep_display), 1,
                         "an order still shown on the screen must still be counted in the badge")

    def test_order_count_cleared_by_reset(self):
        """Resetting the display clears the screen, so it must clear the badge too."""
        prep_display = self.env['pos.prep.display'].create({
            'name': 'Kitchen Display',
            'pos_config_ids': [Command.link(self.config.id)],
        })
        self._send_order_to_display(prep_display)

        self.assertEqual(self._screen_order_count(prep_display), 1)
        self.assertEqual(self._badge_order_count(prep_display), 1)

        prep_display.reset()

        self.assertEqual(self._screen_order_count(prep_display), 0,
                         "reset removes the order from the preparation screen")
        self.assertEqual(self._badge_order_count(prep_display), 0,
                         "reset must leave no outstanding work in the badge either")
