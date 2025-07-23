from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import traceback

_logger = logging.getLogger(__name__)

class Student(models.Model):
    _name = 'school.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    roll_number = fields.Char(string='Roll Number', readonly=True, tracking=True, copy=False)
    admission_number = fields.Char(string='Admission Number', tracking=True, readonly=True, copy=False)
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', required=True, tracking=True)
    blood_group = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-'),
        ('o+', 'O+'),
        ('o-', 'O-')
    ], string='Blood Group', tracking=True)
    address = fields.Text(string='Address', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    parent_name = fields.Char(string='Parent/Guardian Name', required=True, tracking=True)
    parent_phone = fields.Char(string='Parent/Guardian Phone', tracking=True)
    parent_email = fields.Char(string='Parent/Guardian Email', tracking=True)
    class_id = fields.Many2one('school.class', string='Class', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admitted', 'Admitted'),
        ('left', 'Left')
    ], string='Status', default='draft', tracking=True)
    admission_date = fields.Date(string='Admission Date', tracking=True)
    leaving_date = fields.Date(string='Leaving Date', tracking=True)
    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance History')
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fee History')
    attendance_count = fields.Integer(compute='_compute_attendance_count', string='Attendance Count')
    fee_count = fields.Integer(compute='_compute_fee_count', string='Fee Count')
    total_fee_amount = fields.Float(compute='_compute_fee_amounts', string='Total Fee Amount')
    paid_fee_amount = fields.Float(compute='_compute_fee_amounts', string='Paid Fee Amount')
    pending_fee_amount = fields.Float(compute='_compute_fee_amounts', string='Pending Fee Amount')

    @api.model
    def _verify_sequences(self):
        """Verify that required sequences exist, create them if they don't"""
        _logger.info("Verifying student sequences")
        IrSequence = self.env['ir.sequence'].sudo()
        
        # Check roll number sequence
        roll_seq = IrSequence.search([('code', '=', 'school.student.roll')])
        if not roll_seq:
            _logger.info("Creating roll number sequence")
            roll_seq = IrSequence.create({
                'name': 'Student Roll Number',
                'code': 'school.student.roll',
                'prefix': 'ROLL/%(year)s/',
                'padding': 4,
            })
        
        # Check admission number sequence
        adm_seq = IrSequence.search([('code', '=', 'school.student')])
        if not adm_seq:
            _logger.info("Creating admission number sequence")
            adm_seq = IrSequence.create({
                'name': 'Student Admission Number',
                'code': 'school.student',
                'prefix': 'ADM/%(year)s/',
                'padding': 4,
            })
        
        return True

    @api.model_create_multi
    def create(self, vals_list):
        # Verify sequences before creating records
        self._verify_sequences()
        
        for vals in vals_list:
            try:
                _logger.info("Generating sequences for new student: %s", vals.get('name'))
                
                # Generate roll number if not provided
                if not vals.get('roll_number'):
                    vals['roll_number'] = self.env['ir.sequence'].sudo().next_by_code('school.student.roll')
                    _logger.info("Generated roll number: %s", vals['roll_number'])
                
                # Generate admission number if not provided
                if not vals.get('admission_number'):
                    vals['admission_number'] = self.env['ir.sequence'].sudo().next_by_code('school.student')
                    _logger.info("Generated admission number: %s", vals['admission_number'])

                # Send SMS notification to parent
                if vals.get('parent_phone'):
                    try:
                        self.env['sms.sms'].sudo().create({
                            'body': f"Dear {vals.get('parent_name')}, your ward {vals.get('name')} has been registered in our school. Admission Number: {vals.get('admission_number')}",
                            'partner_id': self.env['res.partner'].sudo().create({
                                'name': vals.get('parent_name'),
                                'phone': vals.get('parent_phone'),
                                'email': vals.get('parent_email'),
                            }).id,
                            'number': vals.get('parent_phone'),
                        })
                        _logger.info("SMS notification sent to parent: %s", vals.get('parent_phone'))
                    except Exception as e:
                        _logger.error("Failed to send SMS: %s", str(e))
            except Exception as e:
                _logger.error("Error preparing student data: %s\n%s", str(e), traceback.format_exc())
                raise

        try:
            result = super().create(vals_list)
            _logger.info("Successfully created %d student records", len(result))
            return result
        except Exception as e:
            _logger.error("Error creating student records: %s\n%s", str(e), traceback.format_exc())
            raise

    @api.depends('attendance_ids')
    def _compute_attendance_count(self):
        for record in self:
            record.attendance_count = len(record.attendance_ids)

    @api.depends('fee_ids')
    def _compute_fee_count(self):
        for record in self:
            record.fee_count = len(record.fee_ids)

    @api.depends('fee_ids', 'fee_ids.amount', 'fee_ids.state')
    def _compute_fee_amounts(self):
        for record in self:
            record.total_fee_amount = sum(record.fee_ids.mapped('amount'))
            record.paid_fee_amount = sum(record.fee_ids.filtered(lambda f: f.state == 'paid').mapped('amount'))
            record.pending_fee_amount = sum(record.fee_ids.filtered(lambda f: f.state in ['pending', 'overdue']).mapped('amount'))

    def action_admit(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_("Only draft students can be admitted."))
            
            record.write({
                'state': 'admitted',
                'admission_date': fields.Date.today()
            })
            
            # Send SMS notification to parent
            if record.parent_phone:
                try:
                    self.env['sms.sms'].create({
                        'body': f"Dear {record.parent_name}, your ward {record.name} has been admitted to our school. Admission Number: {record.admission_number}",
                        'partner_id': self.env['res.partner'].create({
                            'name': record.parent_name,
                            'phone': record.parent_phone,
                            'email': record.parent_email,
                        }).id,
                        'number': record.parent_phone,
                    })
                except Exception as e:
                    _logger.error(f"Failed to send SMS: {str(e)}")

    def action_leave(self):
        for record in self:
            if record.state != 'admitted':
                raise ValidationError(_("Only admitted students can leave."))
            
            record.write({
                'state': 'left',
                'leaving_date': fields.Date.today()
            })
            
            # Send SMS notification to parent
            if record.parent_phone:
                try:
                    self.env['sms.sms'].create({
                        'body': f"Dear {record.parent_name}, your ward {record.name} has left our school. Admission Number: {record.admission_number}",
                        'partner_id': self.env['res.partner'].create({
                            'name': record.parent_name,
                            'phone': record.parent_phone,
                            'email': record.parent_email,
                        }).id,
                        'number': record.parent_phone,
                    })
                except Exception as e:
                    _logger.error(f"Failed to send SMS: {str(e)}")

    def action_test(self):
        pass




