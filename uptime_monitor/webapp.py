"""
Flask web application for dashboard and API.
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func
import logging

from uptime_monitor.config import get_config
from uptime_monitor.database import (
    get_session, MonitorModel, CheckResult, Incident,
    UptimeStats, PushMonitor as PushMonitorModel
)

logger = logging.getLogger(__name__)

app = Flask(__name__,
            template_folder='templates',
            static_folder='../static')


def init_app():
    """Initialize Flask app with configuration"""
    config = get_config()
    web_config = config.get_web_config()

    app.config['SECRET_KEY'] = web_config['secret_key']
    app.config['JSON_SORT_KEYS'] = False

    return app


@app.route('/')
def dashboard():
    """Main dashboard view"""
    session = get_session()
    try:
        config = get_config()

        # Get all monitors with their latest status
        monitors = session.query(MonitorModel).filter_by(enabled=True).all()

        # Organize monitors by group
        groups = config.get_monitors_by_group()
        group_order = config.get_group_display_order()

        # Get latest check results for each monitor
        monitor_statuses = {}
        for monitor in monitors:
            latest_check = session.query(CheckResult)\
                .filter_by(monitor_id=monitor.id)\
                .order_by(CheckResult.timestamp.desc())\
                .first()

            # Check for ongoing incident
            ongoing_incident = session.query(Incident)\
                .filter_by(monitor_id=monitor.id, ended_at=None)\
                .first()

            # Extract target info from config based on monitor type
            target_info = _get_monitor_target(monitor.type, monitor.config)

            monitor_statuses[monitor.name] = {
                'id': monitor.id,
                'name': monitor.name,
                'type': monitor.type,
                'group': monitor.group_name or 'Ungrouped',
                'status': latest_check.status if latest_check else 'unknown',
                'response_time': latest_check.response_time if latest_check else None,
                'last_checked': latest_check.timestamp if latest_check else None,
                'error_message': latest_check.error_message if latest_check else None,
                'ongoing_incident': ongoing_incident.id if ongoing_incident else None,
                'uptime_24h': _calculate_uptime(session, monitor.id, hours=24),
                'uptime_7d': _calculate_uptime(session, monitor.id, days=7),
                'uptime_30d': _calculate_uptime(session, monitor.id, days=30),
                'interval': monitor.interval,
                'target': target_info,
                'config': monitor.config
            }

        # Calculate overall statistics
        total_monitors = len(monitors)
        up_count = sum(1 for m in monitor_statuses.values() if m['status'] == 'up')
        down_count = sum(1 for m in monitor_statuses.values() if m['status'] == 'down')
        overall_uptime = (up_count / total_monitors * 100) if total_monitors > 0 else 0

        return render_template('dashboard.html',
                             monitor_statuses=monitor_statuses,
                             group_order=group_order,
                             overall_uptime=overall_uptime,
                             total_monitors=total_monitors,
                             up_count=up_count,
                             down_count=down_count)
    finally:
        session.close()


@app.route('/monitor/<int:monitor_id>')
def monitor_detail(monitor_id):
    """Individual monitor detail page"""
    session = get_session()
    try:
        monitor = session.query(MonitorModel).filter_by(id=monitor_id).first()
        if not monitor:
            return "Monitor not found", 404

        # Get latest check
        latest_check = session.query(CheckResult)\
            .filter_by(monitor_id=monitor.id)\
            .order_by(CheckResult.timestamp.desc())\
            .first()

        # Get recent incidents
        recent_incidents = session.query(Incident)\
            .filter_by(monitor_id=monitor.id)\
            .order_by(Incident.started_at.desc())\
            .limit(20)\
            .all()

        # Get uptime statistics
        uptime_stats = {
            '24h': _calculate_uptime(session, monitor.id, hours=24),
            '7d': _calculate_uptime(session, monitor.id, days=7),
            '30d': _calculate_uptime(session, monitor.id, days=30)
        }

        return render_template('monitor_detail.html',
                             monitor=monitor,
                             latest_check=latest_check,
                             recent_incidents=recent_incidents,
                             uptime_stats=uptime_stats)
    finally:
        session.close()


@app.route('/api/status')
def api_status():
    """JSON API for dashboard status updates (AJAX polling)"""
    session = get_session()
    try:
        monitors = session.query(MonitorModel).filter_by(enabled=True).all()

        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'monitors': []
        }

        for monitor in monitors:
            latest_check = session.query(CheckResult)\
                .filter_by(monitor_id=monitor.id)\
                .order_by(CheckResult.timestamp.desc())\
                .first()

            ongoing_incident = session.query(Incident)\
                .filter_by(monitor_id=monitor.id, ended_at=None)\
                .first()

            result['monitors'].append({
                'id': monitor.id,
                'name': monitor.name,
                'type': monitor.type,
                'group': monitor.group_name or 'Ungrouped',
                'status': latest_check.status if latest_check else 'unknown',
                'response_time': latest_check.response_time if latest_check else None,
                'last_checked': latest_check.timestamp.isoformat() if latest_check else None,
                'error_message': latest_check.error_message if latest_check else None,
                'ongoing_incident_id': ongoing_incident.id if ongoing_incident else None
            })

        return jsonify(result)
    finally:
        session.close()


@app.route('/api/monitor/<int:monitor_id>/history')
def api_monitor_history(monitor_id):
    """JSON API for monitor history data (for charts)"""
    session = get_session()
    try:
        # Get time range from query params (default: last 24 hours)
        hours = request.args.get('hours', 24, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get check results
        results = session.query(CheckResult)\
            .filter(
                CheckResult.monitor_id == monitor_id,
                CheckResult.timestamp >= since
            )\
            .order_by(CheckResult.timestamp.asc())\
            .all()

        data = {
            'monitor_id': monitor_id,
            'hours': hours,
            'data_points': []
        }

        for result in results:
            data['data_points'].append({
                'timestamp': result.timestamp.isoformat(),
                'status': result.status,
                'response_time': result.response_time
            })

        return jsonify(data)
    finally:
        session.close()


@app.route('/api/push/<int:monitor_id>/<secret_key>', methods=['POST', 'GET'])
def api_push_update(monitor_id, secret_key):
    """
    Push monitor endpoint.

    External services POST to this endpoint to update their status.
    """
    session = get_session()
    try:
        # Find push monitor
        push_monitor = session.query(PushMonitorModel)\
            .filter_by(monitor_id=monitor_id)\
            .first()

        if not push_monitor:
            return jsonify({'error': 'Push monitor not found'}), 404

        # Verify secret key
        if push_monitor.secret_key != secret_key:
            return jsonify({'error': 'Invalid secret key'}), 403

        # Update last push time
        push_monitor.last_push_at = datetime.utcnow()

        # Calculate next expected time
        next_expected = push_monitor.last_push_at + timedelta(
            seconds=push_monitor.expected_interval + push_monitor.grace_period
        )
        push_monitor.next_expected_at = next_expected

        session.commit()

        logger.info(f"Push received for monitor ID {monitor_id}")

        return jsonify({
            'success': True,
            'monitor_id': monitor_id,
            'received_at': push_monitor.last_push_at.isoformat(),
            'next_expected_by': next_expected.isoformat()
        })

    except Exception as e:
        logger.error(f"Error processing push for monitor {monitor_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@app.route('/debug')
def debug_data():
    """Debug endpoint to see what data is being passed to template"""
    session = get_session()
    try:
        config = get_config()
        monitors = session.query(MonitorModel).filter_by(enabled=True).all()
        groups = config.get_monitors_by_group()
        group_order = config.get_group_display_order()

        # Get latest check results for each monitor
        monitor_statuses = {}
        for monitor in monitors:
            latest_check = session.query(CheckResult)\
                .filter_by(monitor_id=monitor.id)\
                .order_by(CheckResult.timestamp.desc())\
                .first()

            target_info = _get_monitor_target(monitor.type, monitor.config)

            monitor_statuses[monitor.name] = {
                'id': monitor.id,
                'name': monitor.name,
                'type': monitor.type,
                'group': monitor.group_name or 'Ungrouped',
                'target': target_info,
                'status': latest_check.status if latest_check else 'unknown',
            }

        debug_info = {
            'total_monitors': len(monitors),
            'group_order': group_order,
            'groups_in_config': list(groups.keys()),
            'monitor_statuses': monitor_statuses
        }

        return jsonify(debug_info)
    finally:
        session.close()


@app.route('/settings')
def settings():
    """Settings/configuration view (read-only)"""
    config = get_config()

    return render_template('settings.html',
                         config=config)


def _get_monitor_target(monitor_type: str, config: dict) -> str:
    """
    Extract human-readable target information from monitor config.

    Args:
        monitor_type: Type of monitor
        config: Monitor configuration dict

    Returns:
        Human-readable target string
    """
    if monitor_type == 'http':
        return config.get('url', 'Unknown')
    elif monitor_type == 'tcp':
        host = config.get('host', 'Unknown')
        port = config.get('port', '')
        return f"{host}:{port}" if port else host
    elif monitor_type == 'ping':
        return config.get('host', 'Unknown')
    elif monitor_type == 'dns':
        hostname = config.get('hostname', 'Unknown')
        record_type = config.get('record_type', 'A')
        resolver = config.get('resolver', '8.8.8.8')
        return f"{hostname} ({record_type}) via {resolver}"
    elif monitor_type == 'websocket':
        return config.get('url', 'Unknown')
    elif monitor_type == 'docker':
        return config.get('container_name', 'Unknown')
    elif monitor_type == 'push':
        return 'Push-based (passive)'
    else:
        return 'Unknown'


def _calculate_uptime(session, monitor_id: int, hours: int = None, days: int = None) -> float:
    """
    Calculate uptime percentage for a monitor over a time period.

    Args:
        session: Database session
        monitor_id: Monitor ID
        hours: Hours to look back
        days: Days to look back

    Returns:
        Uptime percentage (0-100)
    """
    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
    elif days:
        since = datetime.utcnow() - timedelta(days=days)
    else:
        since = datetime.utcnow() - timedelta(hours=24)

    # Get total checks
    total_checks = session.query(func.count(CheckResult.id))\
        .filter(
            CheckResult.monitor_id == monitor_id,
            CheckResult.timestamp >= since
        )\
        .scalar()

    if total_checks == 0:
        return 0.0

    # Get successful checks
    successful_checks = session.query(func.count(CheckResult.id))\
        .filter(
            CheckResult.monitor_id == monitor_id,
            CheckResult.timestamp >= since,
            CheckResult.status == 'up'
        )\
        .scalar()

    return (successful_checks / total_checks * 100) if total_checks > 0 else 0.0


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500


# Template filters
@app.template_filter('timeago')
def timeago_filter(timestamp):
    """Convert timestamp to time ago string"""
    if not timestamp:
        return 'Never'

    now = datetime.utcnow()
    if timestamp.tzinfo:
        timestamp = timestamp.replace(tzinfo=None)

    diff = now - timestamp

    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    else:
        return f"{int(seconds / 86400)}d ago"


@app.template_filter('duration')
def duration_filter(seconds):
    """Convert seconds to human-readable duration"""
    if not seconds:
        return 'N/A'

    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m {int(seconds % 60)}s"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"
