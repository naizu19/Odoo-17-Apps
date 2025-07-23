from odoo import models, fields, api

class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Class Name', required=True, tracking=True)
    code = fields.Char(string='Class Code', required=True, tracking=True)
    capacity = fields.Integer(string='Capacity', default=30)
    active = fields.Boolean(default=True)
    student_ids = fields.One2many('school.student', 'class_id', string='Students')
    description = fields.Text(string='Description') 