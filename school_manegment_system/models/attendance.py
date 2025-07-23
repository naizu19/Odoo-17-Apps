from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class Attendance(models.Model):
    _name = 'school.attendance'
    _description = 'Student Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _sql_constraints = [
        ('unique_student_date', 'unique(student_id, date)', 'Attendance for this student on this date already exists!'),
    ]

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    student_id = fields.Many2one('school.student', string='Student', required=True, tracking=True,
                                domain="[('state', '=', 'admitted')]")
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late')
    ], string='Status', required=True, default='present', tracking=True)
    remark = fields.Text(string='Remarks', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], string='Stage', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        # Prevent duplicate attendance for the same student and date
        if vals.get('student_id') and vals.get('date'):
            existing = self.search([
                ('student_id', '=', vals['student_id']),
                ('date', '=', vals['date'])
            ], limit=1)
            if existing:
                raise ValidationError(_('Attendance is already set for this student on this date!'))
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('school.attendance') or _('New')
        return super(Attendance, self).create(vals)

    def write(self, vals):
        # Assign sequence if name is still 'New' and not set
        for rec in self:
            if ('name' not in vals or vals['name'] == _('New')) and rec.name == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('school.attendance') or _('New')
        # Prevent duplicate attendance for the same student and date
        if 'student_id' in vals or 'date' in vals:
            for rec in self:
                student_id = vals.get('student_id', rec.student_id.id)
                date = vals.get('date', rec.date)
                existing = self.search([
                    ('student_id', '=', student_id),
                    ('date', '=', date),
                    ('id', '!=', rec.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_('Attendance is already set for this student on this date!'))
        return super(Attendance, self).write(vals)

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_("Only draft attendance can be confirmed."))
            
            record.write({'state': 'confirmed'})
            
            # Send SMS notification to parent if student is absent
            if record.status == 'absent' and record.student_id.parent_phone:
                try:
                    self.env['sms.sms'].create({
                        'body': f"Dear {record.student_id.parent_name}, this is to inform you that your ward {record.student_id.name} was absent on {record.date}.",
                        'partner_id': self.env['res.partner'].create({
                            'name': record.student_id.parent_name,
                            'phone': record.student_id.parent_phone,
                            'email': record.student_id.parent_email,
                        }).id,
                        'number': record.student_id.parent_phone,
                    })
                except Exception as e:
                    _logger.error(f"Failed to send SMS: {str(e)}") 