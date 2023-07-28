from odoo import models, fields, api


class Registration(models.Model):
    _name = 'ot.registration'
    _description = 'Registration information'

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for record in self:
            if record.project_id:
                record.name = record.employee_id.name + ' - ' + record.project_id.name
    name = fields.Char(default='OT Registration')
    state = fields.Selection(
        [('draft','Draft'),
         ('to approve','To Approve'),
         ('pm approved','PM Approved'),
         ('dl approved','DL Approved'),
         ('refused','Refused')],
        default='draft'
    )
    project_id = fields.Many2one('project.project', required=True)

    def _get_employee_id(self):
        employee = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1)
        return employee
    employee_id = fields.Many2one('hr.employee',
                                  default=_get_employee_id,
                                  readonly=True)

    lead_id = fields.Many2one(
        'hr.employee',
        string='Department Lead',
        related='employee_id.parent_id')

    @api.depends('lead_id', 'project_id')
    def _compute_approver(self):
        for record in self:
            if not record.project_id:
                record.approve_id = record.lead_id
            else:
                if record.state == 'draft' or record.state == 'to approve':
                    record.approve_id = self.env['hr.employee'].search(
                        [('user_id','=',record.project_id.user_id.id)],
                        limit=1)
                elif record.state == 'pm approved':
                    record.approve_id = record.lead_id
                elif record.state == 'dl approved' or record.state == 'refused':
                    record.approve_id = False
    approve_id = fields.Many2one('hr.employee',
                                 string='Approver',
                                 compute='_compute_approver',
                                 store=True,
                                 readonly=False,
                                 required=True)
    request_line_ids = fields.One2many('ot.request.line',
                                       'registration_id')

    @api.depends('request_line_ids')
    def _compute_total_ot(self):
        for record in self:
            record.total_ot = len(record.request_line_ids)
    total_ot = fields.Integer(string='Total OT',
                              compute='_compute_total_ot',
                              store=True)
    ot_month = fields.Date(string='OT Month')

    def submit_draft(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'to approve'
        return True


class RequestLine(models.Model):
    _name = 'ot.request.line'
    _description = 'Request line information'

    name = fields.Char(related='registration_id.name')
    start_time = fields.Datetime()
    end_time = fields.Datetime()
    ot_category = fields.Selection(
        [('undefined','Undefined'),
         ('ordinary day', 'Ordinary day'),
         ('holiday', 'Holiday')]
    )
    from_home = fields.Boolean(string='WFH')
    ot_hours = fields.Float()
    job_taken = fields.Char()
    state = fields.Selection(
        [('draft','Draft'),
         ('to approve','To Approve'),
         ('pm approved','PM Approved'),
         ('dl approved','DL Approved'),
         ('refused','Refused')],
        related='registration_id.state',
        store=True)
    late_approved = fields.Boolean()
    hr_notes = fields.Char()
    attendance_notes = fields.Char()
    warning = fields.Char()
    registration_id = fields.Many2one('ot.registration')
    employee_id = fields.Many2one(related='registration_id.employee_id')
    project_id = fields.Many2one(related='registration_id.project_id')

    @api.depends('employee_id')
    def _compute_intern(self):
        for record in self:
            record.is_intern = True
    is_intern = fields.Boolean(compute='_compute_intern')


class Employee(models.Model):
    _inherit = 'hr.employee'


class Project(models.Model):
    _inherit = 'project.project'
