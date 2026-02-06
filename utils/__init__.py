# Utils package
from .ai_generator import AIQuotationGenerator, AIEmailGenerator, log_ai_usage
from .pdf_generator import PDFQuotationGenerator
from .email_sender import EmailSender, send_payment_reminder
from .contract_generator import ContractGenerator, SignatureVerifier, generate_contract_pdf_content

__all__ = [
    'AIQuotationGenerator',
    'AIEmailGenerator',
    'log_ai_usage',
    'PDFQuotationGenerator',
    'EmailSender',
    'send_payment_reminder',
    'ContractGenerator',
    'SignatureVerifier',
    'generate_contract_pdf_content',
]

# Import utilities that need database
try:
    from .calendar_manager import CalendarManager, EventConflictChecker
    from .ical_generator import ICalGenerator, generate_ical_from_events
    from .analytics import RevenueAnalyzer, CustomerAnalyzer, ProjectAnalyzer, AIUsageAnalyzer, DashboardAnalytics
    from .chart_generator import ChartGenerator, create_dashboard_charts
    from .invoice_generator import InvoiceGenerator, generate_timesheet_report
    from .notification_manager import NotificationManager, NotificationTemplate, send_bulk_notifications
    from .notification_rules import NotificationRule, NotificationEventType, get_rule, get_all_rules, check_and_notify
    from .portal_auth import PortalAuth, PortalSession, generate_portal_link, validate_portal_token
    from .auth_manager import AuthManager, SessionManager, PermissionChecker, init_admin_user
    from .activity_logger import ActivityLogger, get_logger
    from .workflow_engine import WorkflowEngine, Workflow, Action, TriggerType, ActionType
    from .workflow_templates import WorkflowTemplates, WorkflowBuilder, init_default_workflows

    __all__.extend([
        'CalendarManager',
        'EventConflictChecker',
        'ICalGenerator',
        'generate_ical_from_events',
        'RevenueAnalyzer',
        'CustomerAnalyzer',
        'ProjectAnalyzer',
        'AIUsageAnalyzer',
        'DashboardAnalytics',
        'ChartGenerator',
        'create_dashboard_charts',
        'InvoiceGenerator',
        'generate_timesheet_report',
        'NotificationManager',
        'NotificationTemplate',
        'send_bulk_notifications',
        'NotificationRule',
        'NotificationEventType',
        'get_rule',
        'get_all_rules',
        'check_and_notify',
        'PortalAuth',
        'PortalSession',
        'generate_portal_link',
        'validate_portal_token',
        'AuthManager',
        'SessionManager',
        'PermissionChecker',
        'init_admin_user',
        'ActivityLogger',
        'get_logger',
        'WorkflowEngine',
        'Workflow',
        'Action',
        'TriggerType',
        'ActionType',
        'WorkflowTemplates',
        'WorkflowBuilder',
        'init_default_workflows',
    ])
except ImportError:
    pass
