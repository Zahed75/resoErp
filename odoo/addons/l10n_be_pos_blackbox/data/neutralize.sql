-- neutralize l10n_be_pos_blackbox
UPDATE pos_blackbox_be
   SET local_ip = '0.0.0.0';

UPDATE pos_config
   SET l10n_be_pos_id = '',
       establishment_number = '8789456149';
