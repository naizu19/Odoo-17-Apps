from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class Fee(models.Model):
    _name = 'school.fee'
    _description = 'School Fee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date desc, id desc'

    name = fields.Char(string='Fee Reference', required=True, copy=False, 
                      readonly=True, default=lambda self: _('New'))
    student_id = fields.Many2one('school.student', string='Student', required=True,
                                domain="[('state', '=', 'admitted')]")
    fee_type = fields.Selection([
        ('tuition', 'Tuition Fee'),
        ('transport', 'Transport Fee'),
        ('library', 'Library Fee'),
        ('other', 'Other')
    ], string='Fee Type', required=True)
    amount = fields.Float(string='Amount', required=True)
    due_date = fields.Date(string='Due Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue')
    ], string='Status', default='draft', tracking=True)
    payment_date = fields.Date(string='Payment Date')
    payment_reference = fields.Char(string='Payment Reference')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('school.fee') or _('New')
        return super(Fee, self).create(vals)

    def _send_sms(self, message):
        """Helper method to send SMS with proper partner creation."""
        self.ensure_one()
        if self.student_id.parent_phone:
            try:
                # Create or get partner for the parent
                partner = self.env['res.partner'].create({
                    'name': self.student_id.parent_name,
                    'phone': self.student_id.parent_phone,
                    'email': self.student_id.parent_email,
                })
                
                # Create and send SMS
                self.env['sms.sms'].create({
                    'partner_id': partner.id,
                    'number': self.student_id.parent_phone,
                    'body': message,
                })
            except Exception as e:
                _logger.error(f"Failed to send SMS: {str(e)}")

    def action_confirm(self):
        self.ensure_one()
        self.state = 'pending'
        message = f"Dear {self.student_id.parent_name}, Fee payment of {self.amount} for {self.fee_type} is due on {self.due_date}. "
        message += f"Please ensure timely payment for {self.student_id.name}."
        self._send_sms(message)

    def action_pay(self):
        self.ensure_one()
        self.state = 'paid'
        self.payment_date = fields.Date.context_today(self)
        message = f"Dear {self.student_id.parent_name}, Thank you for the payment of {self.amount} for {self.fee_type}. "
        message += f"Payment received for {self.student_id.name}."
        self._send_sms(message)

    def action_overdue(self):
        self.ensure_one()
        self.state = 'overdue'
        message = f"Dear {self.student_id.parent_name}, This is a reminder that fee payment of {self.amount} for {self.fee_type} "
        message += f"is overdue for {self.student_id.name}. Please make the payment at the earliest."
        self._send_sms(message) 