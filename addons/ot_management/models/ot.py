from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


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
         ('to approve', 'To Approve'),
         ('pm approved', 'PM Approved'),
         ('dl approved', 'DL Approved'),
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
        related='employee_id.parent_id')

    @api.depends('lead_id', 'project_id')
    def _compute_approver(self):
        for record in self:
            if not record.project_id:
                record.approve_id = record.lead_id
            else:
                if record.state == 'draft' or record.state == 'to approve':
                    record.approve_id = self.env['hr.employee'].search(
                        [('user_id', '=', record.project_id.user_id.id)],
                        limit=1)
                elif record.state == 'pm approved':
                    record.approve_id = record.lead_id
                elif record.state == 'dl approved' or record.state == 'refused':
                    record.approve_id = False
    approve_id = fields.Many2one('hr.employee',
                                 'Approver',
                                 compute='_compute_approver',
                                 store=True,
                                 readonly=False,
                                 required=True)
    request_line_ids = fields.One2many('ot.request.line',
                                       'registration_id',
                                       ondelete='cascade')

    @api.depends('request_line_ids')
    def _compute_total_ot(self):
        for record in self:
            if record.request_line_ids:
                res = 0
                for line in record.request_line_ids:
                    res += line.ot_hours
                record.total_ot = res
    total_ot = fields.Integer('Total OT hours', compute='_compute_total_ot', store=True)

    @api.depends('request_line_ids')
    def _compute_ot_month(self):
        for record in self:
            if record.request_line_ids:
                record.ot_month = record.request_line_ids[0].start_time.strftime('%m/%Y')
    ot_month = fields.Char('OT month', compute='_compute_ot_month')

    def submit_draft(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'to approve'
        return True

    @api.model
    def create(self, values):
        if 'request_line_ids' not in values:
            values['request_line_ids'] = False
        return super(Registration, self).create(values)

    @api.constrains('request_line_ids')
    def _check_request_lines(self):
        for record in self:
            if not record.request_line_ids:
                raise ValidationError('At least one corresponding request line must be created')


def float_time(value):
    vals = value.split(':')
    res = float(vals[0]) + float(vals[1]) / 60
    return res


class RequestLine(models.Model):
    _name = 'ot.request.line'
    _description = 'Request line information'

    name = fields.Char(related='registration_id.name')
    start_time = fields.Datetime('From', default=fields.Datetime().today(), required=True)
    end_time = fields.Datetime('To', default=fields.Datetime().today(), required=True)

    @api.onchange('start_time', 'end_time')
    def _onchange_ot_category(self):
        for record in self:
            float_end = float_time(record.end_time.strftime('%H:%M'))
            float_start = float_time(record.start_time.strftime('%H:%M'))
            float_done = float_time('17:30')
            if float_end - float_start >= 1 or float_start > float_done:
                if record.start_time.strftime('%a') in ['Sat', 'Sun']:
                    record.ot_category = 'weekend'
                else:
                    record.ot_category = 'workday'
            else:
                record.ot_category = 'undefined'
    ot_category = fields.Selection(
        [('undefined', 'Undefined'),
         ('weekend', 'Weekend'),
         ('workday', 'Workday')],
        'OT category',
        default=False
    )
    from_home = fields.Boolean(string='WFH')

    @api.depends('start_time', 'end_time')
    def _compute_ot_hours(self):
        for record in self:
            record.ot_hours = int((record.end_time - record.start_time).total_seconds() / 3600.0)
    ot_hours = fields.Integer('OT hours', compute='_compute_ot_hours', store=True)
    job_taken = fields.Char('Job taken', default='N/A', required=True)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('to approve', 'To Approve'),
         ('pm approved', 'PM Approved'),
         ('dl approved', 'DL Approved'),
         ('refused', 'Refused')],
        related='registration_id.state',
        store=True)
    late_approved = fields.Boolean('Late approved')
    hr_notes = fields.Text('HR notes', readonly=True)
    attendance_notes = fields.Text('Attendance notes', readonly=True)
    warning = fields.Char(default='Exceed OT plan', readonly=True)
    registration_id = fields.Many2one('ot.registration')
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
            if record.start_time.date() != record.end_time.date():
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
