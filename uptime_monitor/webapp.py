"""
Flask web application for dashboard and API.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from datetime import datetime, timedelta
from sqlalchemy import func
import logging
import yaml
import os

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

# ============================================================================
# Monitor Management Routes
# ============================================================================

def _load_yaml_config():
    """Load config.yaml file"""
    config_path = os.path.join(os.getcwd(), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def _save_yaml_config(config_data):
    """Save config.yaml file"""
    config_path = os.path.join(os.getcwd(), 'config.yaml')
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)


def _reload_config():
    """Reload configuration (requires app restart for now)"""
    # For now, we'll require a manual restart
    # Future: Could implement hot reload by restarting scheduler
    pass


@app.route('/monitors/manage')
def monitors_manage():
    """Monitor management page"""
    try:
        yaml_config = _load_yaml_config()
        monitors = yaml_config.get('monitors', [])
        
        # Get target info for each monitor
        for monitor in monitors:
            monitor['target'] = _get_monitor_target(monitor['type'], monitor.get('config', {}))
        
        return render_template('monitors_manage.html', monitors=monitors)
    except Exception as e:
        logger.error(f"Error loading monitors: {e}")
        return f"Error loading monitors: {str(e)}", 500


@app.route('/monitors/add', methods=['GET', 'POST'])
def monitor_add():
    """Add new monitor"""
    if request.method == 'POST':
        try:
            yaml_config = _load_yaml_config()
            
            # Build monitor config from form data
            monitor_config = _build_monitor_from_form(request.form)
            
            # Check for duplicate name
            existing_names = [m['name'] for m in yaml_config.get('monitors', [])]
            if monitor_config['name'] in existing_names:
                return render_template('monitor_form.html', 
                                     error="Monitor name already exists",
                                     groups=_get_groups_list(),
                                     monitor=None)
            
            # Add to config
            if 'monitors' not in yaml_config:
                yaml_config['monitors'] = []
            yaml_config['monitors'].append(monitor_config)
            
            # Save config
            _save_yaml_config(yaml_config)

            # Hot reload monitors
            from uptime_monitor.main import get_scheduler
            scheduler = get_scheduler()
            if scheduler:
                scheduler.reload_monitors()

            logger.info(f"Added new monitor: {monitor_config['name']}")
            return redirect(url_for('monitors_manage'))
            
        except Exception as e:
            logger.error(f"Error adding monitor: {e}")
            return render_template('monitor_form.html',
                                 error=f"Error: {str(e)}",
                                 groups=_get_groups_list(),
                                 monitor=None)
    
    # GET request - show form
    return render_template('monitor_form.html', 
                         monitor=None,
                         groups=_get_groups_list())


@app.route('/monitors/edit/<int:monitor_index>', methods=['GET', 'POST'])
def monitor_edit(monitor_index):
    """Edit existing monitor"""
    try:
        yaml_config = _load_yaml_config()
        monitors = yaml_config.get('monitors', [])
        
        if monitor_index >= len(monitors):
            return "Monitor not found", 404
        
        if request.method == 'POST':
            # Build updated monitor config
            monitor_config = _build_monitor_from_form(request.form)
            
            # Check for duplicate name (excluding current monitor)
            existing_names = [m['name'] for i, m in enumerate(monitors) if i != monitor_index]
            if monitor_config['name'] in existing_names:
                return render_template('monitor_form.html',
                                     error="Monitor name already exists",
                                     groups=_get_groups_list(),
                                     monitor=monitors[monitor_index])
            
            # Update monitor
            monitors[monitor_index] = monitor_config
            _save_yaml_config(yaml_config)

            # Hot reload monitors
            from uptime_monitor.main import get_scheduler
            scheduler = get_scheduler()
            if scheduler:
                scheduler.reload_monitors()

            logger.info(f"Updated monitor: {monitor_config['name']}")
            return redirect(url_for('monitors_manage'))
        
        # GET request - show form with existing data
        return render_template('monitor_form.html',
                             monitor=monitors[monitor_index],
                             groups=_get_groups_list())
                             
    except Exception as e:
        logger.error(f"Error editing monitor: {e}")
        return f"Error: {str(e)}", 500


@app.route('/monitors/delete/<int:monitor_index>')
def monitor_delete(monitor_index):
    """Delete monitor"""
    try:
        yaml_config = _load_yaml_config()
        monitors = yaml_config.get('monitors', [])
        
        if monitor_index >= len(monitors):
            return "Monitor not found", 404
        
        deleted_name = monitors[monitor_index]['name']
        del monitors[monitor_index]

        _save_yaml_config(yaml_config)

        # Hot reload monitors
        from uptime_monitor.main import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            scheduler.reload_monitors()

        logger.info(f"Deleted monitor: {deleted_name}")
        return redirect(url_for('monitors_manage'))
        
    except Exception as e:
        logger.error(f"Error deleting monitor: {e}")
        return f"Error: {str(e)}", 500


def _build_monitor_from_form(form):
    """Build monitor configuration dict from form data"""
    monitor_type = form.get('type')
    
    # Basic config
    monitor = {
        'name': form.get('name'),
        'type': monitor_type,
        'enabled': 'enabled' in form,
        'group': form.get('group') or None,
        'interval': int(form.get('interval', 60)),
        'timeout': int(form.get('timeout', 10)),
        'retry_count': 1,
        'config': {},
        'notifications': [],
        'alert_on': ['down', 'up']
    }
    
    # Type-specific config
    if monitor_type == 'http':
        monitor['config'] = {
            'url': form.get('http_url'),
            'method': form.get('http_method', 'GET'),
            'expected_status_codes': [int(c.strip()) for c in form.get('http_expected_codes', '200').split(',')],
            'verify_ssl': True
        }
    elif monitor_type == 'tcp':
        monitor['config'] = {
            'host': form.get('tcp_host'),
            'port': int(form.get('tcp_port'))
        }
    elif monitor_type == 'ping':
        monitor['config'] = {
            'host': form.get('ping_host'),
            'packet_count': int(form.get('ping_count', 3))
        }
    elif monitor_type == 'dns':
        monitor['config'] = {
            'hostname': form.get('dns_hostname'),
            'record_type': form.get('dns_record_type', 'A'),
            'resolver': form.get('dns_resolver', '8.8.8.8')
        }
    elif monitor_type == 'websocket':
        monitor['config'] = {
            'url': form.get('ws_url')
        }
    elif monitor_type == 'docker':
        monitor['config'] = {
            'container_name': form.get('docker_container')
        }
    
    return monitor


def _get_groups_list():
    """Get list of existing groups from config"""
    try:
        yaml_config = _load_yaml_config()
        groups = set()
        
        # Get groups from monitors
        for monitor in yaml_config.get('monitors', []):
            if monitor.get('group'):
                groups.add(monitor['group'])
        
        # Get groups from groups section
        for group in yaml_config.get('groups', []):
            groups.add(group['name'])
        
        return sorted(list(groups))
    except:
        return []


@app.route('/monitors/reload')
def monitors_reload():
    """Reload monitor configuration"""
    try:
        # This requires restarting the service
        return render_template('reload_required.html')
    except Exception as e:
        return f"Error: {str(e)}", 500
