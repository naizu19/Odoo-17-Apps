from odoo import http
from odoo.http import request
import logging
import traceback
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)

class SchoolWebsite(http.Controller):

    def _handle_access(self, model_name):
        try:
            request.env[model_name].sudo().check_access_rights('create')
            return True
        except AccessError as e:
            _logger.error("Access rights error for model %s: %s", model_name, str(e))
            return False

    @http.route(['/school/enroll'], type='http', auth='public', website=True, methods=['GET'])
    def enrollment_form(self, **kw):
        try:
            if not self._handle_access('school.student'):
                return request.render('website.403')

            classes = request.env['school.class'].sudo().search([])
            _logger.info("Found %d classes for enrollment form", len(classes))
            message = request.session.pop('enrollment_success', None)
            return request.render('school_manegment_system.student_enrollment_form', {
                'classes': classes,
                'message': message
            })
        except Exception as e:
            _logger.error("Error in enrollment form: %s\n%s", str(e), traceback.format_exc())
            return request.render('website.http_error', {'status_code': 500})

    @http.route(['/school/enroll'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def submit_enrollment(self, **post):
        try:
            _logger.info("Starting student enrollment with data: %s", post)
            
            if not self._handle_access('school.student'):
                _logger.error("Access denied for student creation")
                return request.render('website.403')

            if not post:
                _logger.warning("No data received in enrollment form")
                return request.redirect('/school/enroll')

            # Validate required fields
            required_fields = ['name', 'date_of_birth', 'gender', 'parent_name', 'class_id']
            missing_fields = [field for field in required_fields if not post.get(field)]
            if missing_fields:
                _logger.warning("Missing required fields: %s", missing_fields)
                return request.render('website.http_error', {
                    'status_code': 'Error',
                    'status_message': f'The following fields are required: {", ".join(missing_fields)}'
                })

            try:
                # Prepare student values
                vals = {
                    'name': post.get('name').strip(),
                    'date_of_birth': post.get('date_of_birth'),
                    'gender': post.get('gender'),
                    'address': post.get('address', '').strip(),
                    'phone': post.get('phone', '').strip(),
                    'email': post.get('email', '').strip(),
                    'parent_name': post.get('parent_name').strip(),
                    'parent_phone': post.get('parent_phone', '').strip(),
                    'parent_email': post.get('parent_email', '').strip(),
                    'state': 'draft'
                }

                if post.get('class_id'):
                    try:
                        vals['class_id'] = int(post.get('class_id'))
                    except (ValueError, TypeError) as e:
                        _logger.error("Invalid class_id value: %s", post.get('class_id'))
                        raise ValidationError("Invalid class selected")

                _logger.info("Attempting to create student with values: %s", vals)
                
                # Create student record using create method
                Student = request.env['school.student'].sudo()
                new_student = Student.create(vals)
                _logger.info("Student created successfully with ID: %s, Roll Number: %s", 
                            new_student.id, new_student.roll_number)

                # Verify creation
                if not new_student.exists():
                    _logger.error("Student creation verification failed")
                    raise ValidationError("Student creation failed - record not found after creation")

                success_message = f"Student {new_student.name} enrolled successfully! Roll Number: {new_student.roll_number}"
                request.session['enrollment_success'] = success_message
                _logger.info("Enrollment success: %s", success_message)
                
                return request.render('school_manegment_system.enrollment_success', {
                    'message': success_message
                })

            except (ValueError, ValidationError) as e:
                _logger.error("Validation error in enrollment: %s\n%s", str(e), traceback.format_exc())
                return request.render('website.http_error', {
                    'status_code': 'Error',
                    'status_message': str(e)
                })

        except Exception as e:
            _logger.error("Error in enrollment submission: %s\n%s", str(e), traceback.format_exc())
            return request.render('website.http_error', {
                'status_code': 'Error',
                'status_message': 'There was an error processing your enrollment. Please try again.'
            })

    @http.route(['/school/enrollment/success'], type='http', auth='public', website=True)
    def enrollment_success(self, **kw):
        message = request.session.get('enrollment_success', 'Enrollment completed successfully!')
        return request.render('school_manegment_system.enrollment_success', {
            'message': message
        })
