{
    'name': "Overtime",

    'summary': """
        Centralize OT information""",

    'description': """
    """,

    'author': "VTI Corp",
    'website': "http://https://vti.com.vn/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Schedule',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','project'],
    'application': True,
    'installable': True,
    'auto_install': False,

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/email_templates_data.xml',
        'views/ot_views.xml'
    ],
    # only loaded in demonstration mode
    # 'demo': [
    # ],
}