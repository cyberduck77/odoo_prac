from odoo import models, fields, api


class Registration(models.Model):
    _name = 'ot.registration'
    _description = 'Registration information'

    name = fields.Char(required=True)

    request_line_ids = fields.One2many('ot.request.line', 'registration_id')
    # user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    # employee_id = fields.Many2one('hr.employee', related=user_id.empl)
    # project_id = fields.Many2one('project.project', required=True)
    # approver_id = fields.Many2one('hr.employee', compute='_compute_approver', required=True, store=True, readonly=False)
    # @api.depends('dl_id', 'project_id')
    # def _compute_approver(self):
    #     for record in self:
    #         if len(record.project_id) == 0:
    #             record.approver_id = record.dl_id
    #         else:
    #             record.approver_id = record.project_id.manager_id
    #
    # dl_id = fields.Many2one('hr.employee', readonly=True)

class RequestLine(models.Model):
    _name = 'ot.request.line'
    _description = 'Request line information'

    name = fields.Char(required=True)

    registration_id = fields.Many2one('ot.registration')
    # from_date = fields.Datetime()
    # to_date = fields.Datetime()
    # ot_category = fields.Selection()
    # work_from_home = fields.Boolean()
    # ot_hours = fields.Float()
    # state = fields.Selection()
    # late_approved = fields.Boolean()
    # hr_notes = fields.Text()
    # attendance_notes = fields.Text()
    # warning = fields.Text()


class Employee(models.Model):
    _inherit = 'hr.employee'

    # registration_ids = fields.One2many('ot.registration', 'employee_id')


class Project(models.Model):
    _inherit = 'project.project'


