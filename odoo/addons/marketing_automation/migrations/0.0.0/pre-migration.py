def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_data
           SET noupdate = TRUE
         WHERE module = 'marketing_automation'
           AND noupdate IS NOT TRUE
           AND name IN (
               'res_partner_category_tag_hot',
               'mailing_list_contact_list',
               'ir_actions_server_partner_tag',
               'ir_actions_server_partner_todo',
               'ir_actions_server_contact_blacklist',
               'ir_actions_server_contact_add_list',
               'ir_actions_server_partner_message'
           )
    """)
