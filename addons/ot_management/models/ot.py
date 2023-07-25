from odoo import models, fields, api


class Registration(models.Model):
    _name = 'ot.registration'
    _description = 'Registration information'

    name = fields.Char(required=True)
    state = fields.Selection(
        [('draft','Draft'),('to approve','To Approve'),('pm approved','PM Approved'),
         ('dl approved','DL Approved'),('refused','Refused')]
    )

    def _get_employee_id(self):
        employee = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1)
        return employee.id
    employee_id = fields.Many2one('hr.employee', default=_get_employee_id, readonly=True, required=True)
    lead_id = fields.Many2one('hr.employee', string='Department Lead', related='employee_id.parent_id', store=True, readonly=True, required=True)

    @api.depends('lead_id', 'project_id')
    def _compute_approver(self):
        for record in self:
            if len(record.project_id) == 0:
                record.approve_id = record.lead_id
    approve_id = fields.Many2one('hr.employee', string='Approver', compute='_compute_approver', store=True, readonly=False, required=True)
    project_id = fields.Many2one('project.project')
    request_line_ids = fields.One2many('ot.request.line', 'registration_id')

    @api.depends('request_line_ids')
    def _compute_total_ot(self):
        for record in self:
            record.total_ot = len(record.request_line_ids)
    total_ot = fields.Integer(string='Total OT', compute='_compute_total_ot', store=True)
    ot_month = fields.Date(string='OT Month')


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

    # registration_id = fields.Many2one('ot.registration', 'employee_ids')


class Project(models.Model):
    _inherit = 'project.project'
