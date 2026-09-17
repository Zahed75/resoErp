# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response

from odoo.addons.portal.controllers.portal import CustomerPortal


class OwnershipPortal(CustomerPortal):
    """Owner self-service: holdings, distributions, report builder."""

    def _ownership_owner(self):
        return request.env['rcloud.owner'].sudo().search(
            [('portal_user_id', '=', request.env.user.id)], limit=1)

    def _check_portal(self):
        if not request.env.user.has_group('base.group_portal') or \
                request.env.user.has_group('base.group_user'):
            return request.redirect('/my')
        return None

    @http.route(['/my/ownership'], type='http', auth='user', website=True)
    def ownership_home(self, **kw):
        redirect = self._check_portal()
        if redirect:
            return redirect
        owner = self._ownership_owner()
        holdings = request.env['rcloud.share.holding'].search(
            [('owner_id', '=', owner.id)])
        values = self._prepare_portal_layout_values()
        values.update({
            'owner': owner,
            'holdings': holdings,
            'page_name': 'ownership',
        })
        return request.render('rcloud_ownership.portal_ownership', values)

    @http.route(['/my/ownership/distributions'], type='http', auth='user',
                website=True)
    def ownership_distributions(self, **kw):
        redirect = self._check_portal()
        if redirect:
            return redirect
        owner = self._ownership_owner()
        lines = request.env['rcloud.distribution.line'].search(
            [('owner_id', '=', owner.id)])
        runs = lines.run_id.sorted(
            key=lambda r: (r.period_start, r.id), reverse=True)
        values = self._prepare_portal_layout_values()
        values.update({
            'owner': owner,
            'runs': runs,
            'page_name': 'ownership_distributions',
        })
        return request.render(
            'rcloud_ownership.portal_distributions', values)

    @http.route(['/my/ownership/reports'], type='http', auth='user',
                website=True)
    def ownership_reports(self, **kw):
        redirect = self._check_portal()
        if redirect:
            return redirect
        owner = self._ownership_owner()
        templates = request.env['rcloud.owner.report.template'].search([
            '|', ('owner_id', '=', False), ('owner_id', '=', owner.id)])
        values = self._prepare_portal_layout_values()
        values.update({
            'owner': owner,
            'templates': templates,
            'page_name': 'ownership_reports',
        })
        return request.render(
            'rcloud_ownership.portal_reports', values)

    @http.route(['/my/ownership/reports/<int:template_id>/csv'],
                type='http', auth='user', website=False)
    def ownership_report_csv(self, template_id, **kw):
        template = request.env['rcloud.owner.report.template'].browse(
            template_id).exists()
        if not template:
            return request.not_found()
        csv_data = template.sudo().render_csv()
        return Response(
            csv_data, content_type='text/csv;charset=utf-8',
            headers=[('Content-Disposition',
                      'attachment; filename="%s.csv"' % template.name)])
