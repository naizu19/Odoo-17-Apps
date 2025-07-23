{
    'name': 'School Management System',
    'version': '1.0',
    'category': 'Education',
    'summary': 'Manage school operations',
    'sequence': 1,
    'description': """
        School Management System
        =======================
        * Student Management
        * Class Management
        * Attendance Management
        * Fee Management
        * SMS Notifications
        * Sale Order Line Access Control
        * Third Party Intigration
    """,
    'author': 'Nazullah',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail',
        'sms',
        'website',
        'sale',
    ],
    'data': [
        'security/sale_security.xml',
        'data/sequences.xml',
        'security/ir.model.access.csv',
        'views/student_views.xml',
        'views/class_views.xml',
        'views/attendance_views.xml',
        'views/fee_views.xml',
        'views/menu_views.xml',
        'views/website_templates.xml',
        'reports/student_report_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 