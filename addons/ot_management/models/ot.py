from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
from odoo.tools import float_round


class Registration(models.Model):
    _name = 'ot.registration'
    _description = 'Registration information'

    def _get_employee_id(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee

    def get_url(self):
        base = self.env['ir.config_parameter'].get_param('web.base.url')
        url_res = base + '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        return url_res

    def action_submit_draft(self):
        if self.state == 'draft' and self.env.uid == self.employee_id.user_id.id:
            self.state = 'to_approve'
            template = self.env.ref('ot_management.submit_ot_mail_template')
            template.sudo().send_mail(self.id, force_send=True)
        else:
            raise AccessError("You're not allowed to submit this draft")
        return True

    def action_turn_to_draft(self):
        if self.state == 'refused' and self.env.uid == self.employee_id.user_id.id:
            self.state = 'draft'
        else:
            raise AccessError("You're not allowed to convert this request back to draft")
        return True

    def action_pm_approve(self):
        if self.state == 'to_approve' and self.env.uid == self.approve_id.user_id.id:
            self.state = 'pm_approved'
            template = self.env.ref('ot_management.pm_approve_mail_template')
            template.sudo().send_mail(self.id, force_send=True)
        else:
            raise AccessError("You're not allowed to approve this request")
        return True

    def action_dl_approve(self):
        if self.state == 'pm_approved' and self.env.uid == self.approve_id.user_id.id:
            self.state = 'dl_approved'
            template = self.env.ref('ot_management.dl_approve_mail_template')
            template.sudo().send_mail(self.id, force_send=True)
        else:
            raise AccessError("You're not allowed to approve this request")
        return True

    def action_refuse(self):
        if self.state == 'to_approve' and self.env.uid == self.approve_id.user_id.id:
            self.state = 'refused'
            template = self.env.ref('ot_management.refuse_mail_template')
            template.sudo().send_mail(self.id, force_send=True)
        else:
            raise AccessError("You're not allowed to refuse this request")
        return True

    @api.onchange('project_id', 'employee_id')
    def _onchange_display_name(self):
        for record in self:
            if record.project_id and record.employee_id:
                record.name = record.employee_id.name + ' - ' + record.project_id.name

    @api.depends('state', 'lead_id', 'project_id')
    def _compute_approve(self):
        for record in self:
            if record.project_id:
                if record.state == 'draft' or record.state == 'to_approve':
                    record.approve_id = self.env['hr.employee'].search(
                        [('user_id', '=', record.project_id.user_id.id)],
                        limit=1
                    )
                elif record.state == 'pm_approved' or record.state == 'dl_approved':
                    record.approve_id = record.lead_id
                elif record.state == 'refused':
                    record.approve_id = False

    @api.depends('request_line_ids')
    def _compute_total_hours(self):
        for record in self:
            if record.request_line_ids:
                res = 0
                for line in record.request_line_ids:
                    res += line.ot_hours
                record.total_hours = res

    @api.depends('request_line_ids')
    def _compute_ot_month(self):
        for record in self:
            if record.request_line_ids:
                record.ot_month = record.request_line_ids[0].start_time.strftime('%m/%Y')

    @api.depends('state')
    def _compute_button_visible(self):
        for record in self:
            record.button_visible = 'none'
            if record.state == 'draft' and self.env.uid == record.employee_id.user_id.id:
                record.button_visible = 'draft'
            if record.state == 'refused' and self.env.uid == record.employee_id.user_id.id:
                record.button_visible = 'refused'
            elif record.state == 'to_approve' and self.env.uid == record.approve_id.user_id.id:
                record.button_visible = 'pm'
            elif record.state == 'pm_approved' and self.env.uid == record.approve_id.user_id.id:
                record.button_visible = 'dl'

    @api.depends('state')
    def _compute_css(self):
        for record in self:
            if record.state != 'draft':
                record.change_css = '<style>.o_form_button_edit {display: none !important;}' \
                                    '.o_dropdown_toggler_btn {display: none !important;}' \
                                    '.o_form_button_create {display: none !important;}</style>'
            else:
                record.change_css = False

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
    employee_id = fields.Many2one('hr.employee', default=_get_employee_id,
                                  readonly=True,
                                  required=True)
    lead_id = fields.Many2one(
        'hr.employee',
        string='Department lead',
        related='employee_id.department_id.manager_id',
        related_sudo=True)
    approve_id = fields.Many2one('hr.employee', string='Approver', compute='_compute_approve',
                                 store=True,
                                 compute_sudo=True)
    request_line_ids = fields.One2many('ot.request.line',
                                       'registration_id')
    total_hours = fields.Float(string='Total OT hours', compute='_compute_total_hours', store=True)
    ot_month = fields.Char(string='OT month', compute='_compute_ot_month')
    button_visible = fields.Selection([('none', 'None'),
                                       ('draft', 'Draft'),
                                       ('refused','Refused'),
                                       ('pm', 'Pm'),
                                       ('dl', 'Dl')],
                                      compute='_compute_button_visible',
                                      compute_sudo=True)
    change_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)

    @api.constrains('request_line_ids', 'employee_id')
    def _check_request_lines(self):
        for record in self:
            if not record.request_line_ids:
                raise ValidationError('At least one corresponding request line must be created')


class RequestLine(models.Model):
    _name = 'ot.request.line'
    _description = 'Request line information'

    @api.onchange('start_time', 'end_time')
    def _onchange_ot_category(self):
        for record in self:
            if (record.start_time.date() - record.end_time.date()).total_seconds() != 0 or \
                    (record.end_time - record.start_time).total_seconds() <= 0:
                record.ot_category = 'undefined'
            else:
                if record.start_time.strftime('%a') in ['Sat', 'Sun']:
                    record.ot_category = 'weekend'
                else:
                    record.ot_category = 'workday'

    @api.depends('start_time', 'end_time')
    def _compute_ot_hours(self):
        for record in self:
            record.ot_hours = float_round((record.end_time - record.start_time).total_seconds() / 3600.0, 2)

    @api.depends('employee_id')
    def _compute_intern(self):
        for record in self:
            record.is_intern = False
            if record.employee_id.job_id.name == 'Trainee':
                record.is_intern = True

    name = fields.Char(related='registration_id.name')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('to_approve', 'To Approve'),
         ('pm_approved', 'PM Approved'),
         ('dl_approved', 'DL Approved'),
         ('refused', 'Refused')],
        related='registration_id.state',
        related_sudo=True,
        store=True)
    start_time = fields.Datetime(string='From', default=fields.Datetime().today(), required=True)
    end_time = fields.Datetime(string='To', default=fields.Datetime().today(), required=True)
    ot_category = fields.Selection(
        [('undefined', 'Undefined'),
         ('weekend', 'Weekend'),
         ('workday', 'Workday')],
        'OT category',
        default='undefined'
    )
    from_home = fields.Boolean(string='WFH')
    ot_hours = fields.Float(string='OT hours', compute='_compute_ot_hours', store=True)
    job_taken = fields.Char(string='Job taken', default='N/A', required=True)
    late_approved = fields.Boolean(string='Late approved',
                                   readonly=True)
    hr_notes = fields.Text(string='HR notes',
                           readonly=True)
    attendance_notes = fields.Text(string='Attendance notes',
                                   readonly=True)
    warning = fields.Char(string='Warning', default='Exceed OT plan',
                          readonly=True)
    registration_id = fields.Many2one('ot.registration',
                                      required=True,
                                      ondelete='cascade')
    employee_id = fields.Many2one(string='By employee', related='registration_id.employee_id')
    project_id = fields.Many2one(string='Project', related='registration_id.project_id')
    is_intern = fields.Boolean(string='Is intern?', compute='_compute_intern', store=True)

    @api.constrains('start_time', 'end_time')
    def _check_valid_time(self):
        for record in self:
            overlapping_records = self.search([
                ('id', '!=', record.id),
                ('start_time', '<', record.end_time),
                ('end_time', '>', record.start_time)
            ])
            if overlapping_records:
                raise ValidationError("Overlapping dates found.")
            if (record.start_time.date() - record.end_time.date()).total_seconds() != 0:
                raise ValidationError("Invalid OT request time")
            if (record.end_time - record.start_time).total_seconds() <= 0:
                raise ValidationError("OT hours must be larger than 0")

    @api.constrains('end_time')
    def _check_time_future(self):
        for record in self:
            if record.end_time > fields.Datetime.now():
                raise ValidationError("Cannot plan OT in the future")
