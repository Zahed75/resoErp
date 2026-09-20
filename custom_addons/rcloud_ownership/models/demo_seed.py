# -*- coding: utf-8 -*-
import random

from odoo import api, fields, models, _
from odoo.exceptions import UserError

DEMO_PREFIX = 'Demo '

FIRST_NAMES = (
    'Aarav', 'Sofia', 'Rahim', 'Elena', 'Karim', 'Meera', 'Daniel', 'Farhana',
    'Vikram', 'Isabella', 'Naveen', 'Zara', 'Rohan', 'Camille', 'Arif',
    'Priya', 'Tariq', 'Lucia', 'Imran', 'Hana', 'Omar', 'Nadia', 'Felix',
    'Amina', 'Sanjay', 'Clara', 'Yusuf', 'Leila', 'Marco', 'Tania', 'Bilal',
    'Iris', 'Kamal', 'Rosa', 'Dev', 'Selin', 'Hassan', 'Maya', 'Jonas',
    'Tahmina',
)
LAST_NAMES = (
    'Chowdhury', 'Rahman', 'Hossain', 'Khan', 'Ahmed', 'Karim', 'Islam',
    'Mia', 'Das', 'Sen', 'Patel', 'Sharma', 'Nair', 'Iqbal', 'Chandra',
    'Bhattacharya', 'Fernandes', 'Silva', 'Rossi', 'Conti', 'Novak', 'Horvat',
    'Tanaka', 'Sato', 'Kim', 'Park', 'Nguyen', 'Tran', 'Ali', 'Begum',
    'Uddin', 'Sikder', 'Barua', 'Debnath', 'Mondol', 'Khatun', 'Sarkar',
    'Akter', 'Haque', 'Dewan',
)


class RcloudOwner(models.Model):
    """One-click demo data seed (menu: Reso Ownership → Generate Demo
    Data). Creates a realistic ownership dataset for two properties and
    is idempotent: it bails out when demo records already exist."""

    _inherit = 'rcloud.owner'

    # ------------------------------------------------------------ entry
    @api.model
    def _load_demo_data(self):
        if self.search(
                [('partner_id.name', '=like', DEMO_PREFIX + '%')], limit=1):
            return self._demo_notification(
                _('Demo data was already generated — nothing was created.'),
                'warning')
        rng = random.Random(20260920)
        today = fields.Date.today()
        counts = {}

        # ------------------------------------------------------ properties
        Property = self.env['rcloud.property'].sudo()
        RoomType = self.env['rcloud.room.type'].sudo()
        prop_sea = Property.search(
            [('name', '=', 'Sea Pearl Resort')], limit=1)
        prop_ocean = Property.search([('code', '=', 'OBR')], limit=1)
        if not prop_ocean:
            prop_ocean = Property.create({
                'name': 'Ocean Breeze Resort',
                'code': 'OBR',
                'city': "Cox's Bazar",
                'phone': '+880 341 64000',
                'email': 'folio@oceanbreeze.example.com',
            })
        room_types = {}
        for prop, kinds in (
                (prop_sea, ('Deluxe King', 'Executive Suite')),
                (prop_ocean, ('Deluxe King', 'Executive Suite'))):
            rts = RoomType.search([('property_id', '=', prop.id)])
            for kind in kinds:
                rt = rts.filtered(lambda r: r.name == kind)[:1]
                if not rt:
                    rt = RoomType.create({
                        'name': kind,
                        'property_id': prop.id,
                        'base_occupancy': 2,
                        'max_occupancy': 3 if kind == 'Deluxe King' else 4,
                        'default_rate': 9500.0 if kind == 'Deluxe King'
                        else 15200.0,
                    })
                room_types[(prop.id, kind)] = rt
        counts['rcloud.property'] = 2

        # ---------------------------------------------------------- owners
        Partner = self.env['res.partner'].sudo()
        owners = []
        used = set()
        while len(owners) < 36:
            name = '%s%s %s' % (
                DEMO_PREFIX, rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES))
            if name in used:
                continue
            used.add(name)
            slug = name.replace(DEMO_PREFIX, '').lower().replace(' ', '.')
            partner = Partner.create({
                'name': name,
                'email': '%s@demo-owners.example.com' % slug,
                'phone': '+880 1%03d-%06d' % (
                    rng.randint(300, 999), rng.randint(0, 999999)),
            })
            roll = rng.random()
            owners.append(self.sudo().create({
                'partner_id': partner.id,
                'kyc_state': 'verified' if roll < 0.78 else (
                    'draft' if roll < 0.9 else 'rejected'),
                'bank_details': 'Demo Bank Ltd., A/C %012d, Routing 09%03d'
                % (rng.randint(10**11, 10**12 - 1), rng.randint(100, 999)),
                'tax_id': 'TIN-%08d' % rng.randint(10**7, 10**8 - 1),
                'payout_preference': 'bank_transfer' if rng.random() < 0.85
                else 'cheque',
            }))
        counts['rcloud.owner'] = len(owners)

        # ------------------------------------------------------ share classes
        expense = self.env['account.account'].sudo().search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', [self.env.company.id]),
        ], limit=1)
        Class = self.env['rcloud.share.class'].sudo()
        classes = {}
        specs = (
            ('Class A — Equity', 'gross_room_revenue', 100, 250000.0,
             12.0, 3.0, 0.0, None),
            ('Class B — NOI Growth', 'noi', 60, 400000.0,
             10.0, 5.0, 5.0, None),
            ('Class C — Room Subset', 'room_subset', 40, 300000.0,
             15.0, 2.0, 0.0, 'Deluxe King'),
        )
        for prop in (prop_sea, prop_ocean):
            for name, rule, units, nominal, fee, reserve, wht, kind in specs:
                vals = {
                    'name': '%s (%s)' % (name, prop.code),
                    'property_id': prop.id,
                    'total_units': units,
                    'unit_nominal_value': nominal,
                    'distribution_rule': rule,
                    'management_fee_pct': fee,
                    'reserve_pct': reserve,
                    'withholding_pct': wht,
                    'expense_account_id': expense.id if expense else False,
                }
                if kind:
                    vals['room_type_ids'] = [
                        (6, 0, [room_types[(prop.id, kind)].id])]
                classes[(prop.id, name)] = Class.create(vals)
        counts['rcloud.share.class'] = len(classes)

        # --------------------------------------------------------- holdings
        # The pre-existing owner (e.g. Ayesha Khan) joins the pool so she
        # shows up in replays too.
        existing = self.search([('partner_id.name', 'not like',
                                 DEMO_PREFIX + '%')], limit=1)
        pool = list(owners)
        if existing:
            pool.append(existing)
        Holding = self.env['rcloud.share.holding'].sudo()
        holders = {}  # share class id -> [owner records]
        for cls in classes.values():
            k = rng.randint(6, 7)
            chosen = rng.sample(pool, k)
            weights = [rng.uniform(1.0, 3.0) for _ in chosen]
            scale = int(cls.total_units * 0.8)
            cls_holders = []
            for owner, w in zip(chosen, weights):
                units = max(1, round(w / sum(weights) * scale))
                Holding.create({
                    'owner_id': owner.id,
                    'share_class_id': cls.id,
                    'units_held': units,
                    'acquired_date': fields.Date.subtract(
                        today, days=rng.randint(20, 350)),
                })
                cls_holders.append(owner)
            holders[cls.id] = cls_holders
        counts['rcloud.share.holding'] = Holding.search_count([])

        # -------------------------------------------------------- transfers
        Transfer = self.env['rcloud.share.transfer'].sudo()
        created = 0
        cls_list = list(classes.values())
        for _i in range(60):
            cls = rng.choice(cls_list)
            candidates = list(
                {o.id: o for o in holders[cls.id]}.values())
            if len(candidates) < 2:
                continue
            from_owner, to_owner = rng.sample(candidates, 2)
            future = rng.random() < 0.25
            when = fields.Date.add(today, days=rng.randint(7, 180)) \
                if future else fields.Date.subtract(
                    today, days=rng.randint(10, 300))
            roll = rng.random()
            if future:
                state = 'approved' if roll < 0.5 else (
                    'submitted' if roll < 0.8 else 'draft')
            elif roll < 0.45:
                state = 'completed'
            elif roll < 0.60:
                state = 'approved'
            elif roll < 0.75:
                state = 'submitted'
            elif roll < 0.90:
                state = 'draft'
            else:
                state = 'rejected'
            units = rng.randint(1, 4)
            if state == 'completed':
                available = Holding.get_holding_on(
                    from_owner, cls, when)
                units = min(units, int(available))
                if units < 1:
                    state, units = 'draft', rng.randint(1, 4)
            Transfer.create({
                'from_owner_id': from_owner.id,
                'to_owner_id': to_owner.id,
                'share_class_id': cls.id,
                'units': units,
                'transfer_date': when,
                'state': state,
            })
            if state == 'completed':
                holders[cls.id].append(to_owner)
            created += 1
        counts['rcloud.share.transfer'] = created

        # ---------------------------------------------- distribution runs
        Run = self.env['rcloud.distribution.run'].sudo()
        Line = self.env['rcloud.distribution.line'].sudo()
        payable = self.env['account.account'].sudo().search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', [self.env.company.id]),
        ], limit=1)
        run_plan = (
            (prop_sea, 0, 'paid'),
            (prop_ocean, 0, 'posted'),
            (prop_sea, 1, 'approved'),
            (prop_ocean, 1, 'computed'),
            (prop_sea, 2, 'draft'),
        )
        runs = []
        for prop, months_ago, target in run_plan:
            start = fields.Date.start_of(
                fields.Date.subtract(today, months=months_ago), 'month')
            end = fields.Date.end_of(start, 'month')
            run = Run.create({
                'property_id': prop.id,
                'period_start': start,
                'period_end': end,
                'revenue_basis': 'gross_room_revenue',
                'total_amount': float(rng.randint(80, 250)) * 10000.0,
            })
            runs.append((run, target))
        counts['rcloud.distribution.run'] = len(runs)
        for run, target in runs:
            if target == 'draft':
                continue
            try:
                run.action_calculate()
            except UserError:
                continue  # no weighted units in period; stays draft
            if target == 'computed':
                continue
            run.action_approve()
            if target == 'approved':
                continue
            if not (payable and expense):
                continue
            try:
                run.action_post()
            except UserError:
                continue
            if target == 'posted':
                continue
            try:
                run.action_mark_paid()
            except UserError:
                pass
        counts['rcloud.distribution.line'] = Line.search_count([])

        # --------------------------------------------------- report templates
        Template = self.env['rcloud.owner.report.template'].sudo()
        Template.create({
            'name': DEMO_PREFIX + 'Owner Statement — Monthly',
            'date_from': fields.Date.subtract(today, months=12),
            'date_to': today,
            'property_ids': [(6, 0, [prop_sea.id, prop_ocean.id])],
            'grouping': 'month',
            'metrics': 'net',
        })
        Template.create({
            'name': DEMO_PREFIX + 'Owner Statement — By Property',
            'date_from': fields.Date.subtract(today, months=12),
            'date_to': today,
            'property_ids': [(6, 0, [prop_sea.id, prop_ocean.id])],
            'grouping': 'property',
            'metrics': 'gross',
        })
        counts['rcloud.owner.report.template'] = 2

        message = _('Created: %s.') % ', '.join(
            '%d %s' % (n, model) for model, n in counts.items())
        return self._demo_notification(message)

    # --------------------------------------------------------- notification
    def _demo_notification(self, message, notif_type='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Ownership demo data'),
                'message': message,
                'type': notif_type,
                'sticky': False,
            },
        }
