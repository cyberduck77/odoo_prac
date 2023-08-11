from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class Registration(models.Model):
    _name = 'ot.registration'
    _description = 'Registration information'

    @api.onchange('project_id', 'employee_id')
    def _onchange_display_name(self):
        for record in self:
            if record.project_id and record.employee_id:
                record.name = record.employee_id.name + ' - ' + record.project_id.name
    name = fields.Char(default='')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('to_approve', 'To Approve'),
         ('pm_approved', 'PM Approved'),
         ('dl_approved', 'DL Approved'),
         ('refused', 'Refused')],
        default='draft',
        required=True
    )
    project_id = fields.Many2one('project.project', required=True)

    def _get_employee_id(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee
    employee_id = fields.Many2one('hr.employee',
                                  default=_get_employee_id,
                                  readonly=True,
                                  required=True)
    lead_id = fields.Many2one(
        'hr.employee',
        'Department lead',
        related='employee_id.department_id.manager_id')

    @api.depends('lead_id', 'project_id')
    def _compute_approve(self):
        for record in self:
            if record.project_id:
                if record.state == 'draft' or record.state == 'to_approve':
                    record.approve_id = self.env['hr.employee'].search(
                        [('user_id', '=', record.project_id.user_id.id)],
                        limit=1
                    )
                elif record.state == 'pm_approved':
                    record.approve_id = record.lead_id
                elif record.state == 'dl_approved' or record.state == 'refused':
                        record.approve_id = False
    approve_id = fields.Many2one('hr.employee',
                                 'Approver',
                                 compute='_compute_approve',
                                 store=True,
                                 readonly=False,
                                 required=True)
    request_line_ids = fields.One2many('ot.request.line',
                                       'registration_id')

    @api.depends('request_line_ids')
    def _compute_total_ot(self):
        for record in self:
            if record.request_line_ids:
                res = 0
                for line in record.request_line_ids:
                    res += line.ot_hours
                record.total_ot = res
    total_ot = fields.Float('Total OT hours', compute='_compute_total_ot', store=True)

    @api.depends('request_line_ids')
    def _compute_ot_month(self):
        for record in self:
            if record.request_line_ids:
                record.ot_month = record.request_line_ids[0].start_time.strftime('%m/%Y')
    ot_month = fields.Char('OT month', compute='_compute_ot_month')

    def submit_draft(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'to_approve'
                template = self.env.ref('ot_management.submit_ot_mail_template')
                template.send_mail(record.id, force_send=True)
        return True

    def pm_approve(self):
        for record in self:
            if record.state == 'to_approve':
                record.state = 'pm_approved'
                template = self.env.ref('ot_management.pm_approve_mail_template')
                template.send_mail(record.id, force_send=True)
        return True

    def dl_approve(self):
        for record in self:
            if record.state == 'pm_approved':
                record.state = 'dl_approved'
                template = self.env.ref('ot_management.dl_approve_mail_template')
                template.send_mail(record.id, force_send=True)
        return True

    def action_refuse(self):
        for record in self:
            if record.state == 'pm_approved' or record.state == 'to_approve':
                record.state = 'refused'
                template = self.env.ref('ot_management.refuse_mail_template')
                template.send_mail(record.id, force_send=True)
        return True

    # @api.model
    # def create(self, values):
    #     # if 'request_line_ids' not in values:
    #     #     values['request_line_ids'] = False
    #     res = super(Registration, self).create(values)
    #     return res

    @api.constrains('request_line_ids', 'employee_id')
    def _check_request_lines(self):
        for record in self:
            if not record.request_line_ids:
                raise ValidationError('At least one corresponding request line must be created')


class RequestLine(models.Model):
    _name = 'ot.request.line'
    _description = 'Request line information'

    name = fields.Char(related='registration_id.name')
    start_time = fields.Datetime('From', default=fields.Datetime().today(), required=True)
    end_time = fields.Datetime('To', default=fields.Datetime().today(), required=True)

    @api.onchange('start_time', 'end_time')
    def _onchange_ot_category(self):
        for record in self:
            if (record.start_time.date() - record.end_time.date()).total_seconds() != 0 or\
                    (record.end_time - record.start_time).total_seconds() <= 0:
                record.ot_category = 'undefined'
            else:
                if record.start_time.strftime('%a') in ['Sat', 'Sun']:
                    record.ot_category = 'weekend'
                else:
                    record.ot_category = 'workday'
    ot_category = fields.Selection(
        [('undefined', 'Undefined'),
         ('weekend', 'Weekend'),
         ('workday', 'Workday')],
        'OT category',
        default='undefined'
    )
    from_home = fields.Boolean(string='WFH')

    @api.depends('start_time', 'end_time')
    def _compute_ot_hours(self):
        for record in self:
            record.ot_hours = float_round((record.end_time - record.start_time).total_seconds() / 3600.0, 2)
    ot_hours = fields.Float('OT hours', compute='_compute_ot_hours', store=True)
    job_taken = fields.Char('Job taken', default='N/A', required=True)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('to_approve', 'To Approve'),
         ('pm_approved', 'PM Approved'),
         ('dl_approved', 'DL Approved'),
         ('refused', 'Refused')],
        related='registration_id.state',
        store=True)
    late_approved = fields.Boolean('Late approved')
    hr_notes = fields.Text('HR notes', readonly=True)
    attendance_notes = fields.Text('Attendance notes', readonly=True)
    warning = fields.Char(default='Exceed OT plan', readonly=True)
    registration_id = fields.Many2one('ot.registration',
                                      required=True,
                                      ondelete='cascade')
    employee_id = fields.Many2one(related='registration_id.employee_id')
    project_id = fields.Many2one(related='registration_id.project_id')

    @api.depends('employee_id')
    def _compute_intern(self):
        for record in self:
            record.is_intern = True
    is_intern = fields.Boolean(compute='_compute_intern')

    @api.constrains('start_time', 'end_time')
    def _check_valid_time(self):
        for record in self:
            if (record.start_time.date() - record.end_time.date()).total_seconds() != 0:
                raise ValidationError("Invalid OT request time")

    @api.constrains('start_time', 'end_time')
    def _check_time_positive(self):
        for record in self:
            if (record.end_time - record.start_time).total_seconds() <= 0:
                raise ValidationError("OT hours must be larger than 0")

    @api.constrains('end_time')
    def _check_time_future(self):
        for record in self:
            if record.end_time > fields.Datetime.now():
                raise ValidationError("Cannot plan OT in the future")


class Employee(models.Model):
    _inherit = 'hr.employee'


class Project(models.Model):
    _inherit = 'project.project'
