"""Carian Observatory monitoring integration panel."""

from pathlib import Path
from datetime import datetime
from textual.widgets import Static, DataTable
from textual.app import ComposeResult
import subprocess
import yaml


class ObservatoryPanel(Static):
    """Grafana and Carian Observatory monitoring integration."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.observatory_path = Path.home() / "git" / "internal" / "repos" / "carian-observatory"
        self.services = []
        self.grafana_url = None

    def compose(self) -> ComposeResult:
        """Create the observatory panel."""
        yield Static("Observatory", classes="panel-title")
        table = DataTable(id="observatory-table")
        table.add_columns("Status", "Service", "Dashboard")
        table.cursor_type = "row"
        yield table

    def on_mount(self) -> None:
        """Load observatory services on mount."""
        self.load_observatory_config()
        self.populate_table()

    def load_observatory_config(self):
        """Load Carian Observatory configuration and services."""
        self.services = []

        if not self.observatory_path.exists():
            return

        # Load Grafana URL from .env
        env_file = self.observatory_path / ".env"
        if env_file.exists():
            self.grafana_url = self._parse_grafana_url(env_file)

        # Load monitoring services from docker-compose
        monitoring_compose = (
            self.observatory_path / "services" / "monitoring" / "docker-compose.yml"
        )

        if monitoring_compose.exists():
            try:
                with open(monitoring_compose, 'r') as f:
                    compose_data = yaml.safe_load(f)

                services = compose_data.get('services', {})

                # Add Grafana
                if 'grafana' in services:
                    self.services.append({
                        'name': 'Grafana',
                        'type': 'dashboard',
                        'url': f"{self.grafana_url}" if self.grafana_url else None,
                        'status': self._check_docker_service('grafana')
                    })

                # Add Prometheus
                if 'prometheus' in services:
                    self.services.append({
                        'name': 'Prometheus',
                        'type': 'metrics',
                        'url': f"{self.grafana_url}/prometheus" if self.grafana_url else None,
                        'status': self._check_docker_service('prometheus')
                    })

                # Add Loki
                if 'loki' in services:
                    self.services.append({
                        'name': 'Loki',
                        'type': 'logs',
                        'url': f"{self.grafana_url}/loki" if self.grafana_url else None,
                        'status': self._check_docker_service('loki')
                    })

                # Add Alertmanager
                if 'alertmanager' in services:
                    self.services.append({
                        'name': 'Alertmanager',
                        'type': 'alerts',
                        'url': f"{self.grafana_url}/alertmanager" if self.grafana_url else None,
                        'status': self._check_docker_service('alertmanager')
                    })

            except Exception as e:
                pass

        # Fallback: add basic services if compose parsing failed
        if not self.services:
            self.services = [
                {'name': 'Grafana', 'type': 'dashboard', 'url': self.grafana_url, 'status': 'unknown'},
                {'name': 'Prometheus', 'type': 'metrics', 'url': None, 'status': 'unknown'},
                {'name': 'Loki', 'type': 'logs', 'url': None, 'status': 'unknown'},
            ]

    def _parse_grafana_url(self, env_file: Path) -> str:
        """Parse Grafana URL from .env file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Look for DOMAIN or GRAFANA_URL
                    if line.startswith('DOMAIN='):
                        domain = line.split('=', 1)[1].strip().strip('"\'')
                        return f"https://observatory.{domain}"
                    elif line.startswith('GRAFANA_URL='):
                        url = line.split('=', 1)[1].strip().strip('"\'')
                        return url
        except Exception:
            pass
        return "http://localhost:3000"

    def _check_docker_service(self, service_name: str) -> str:
        """Check if docker service is running.

        Returns: 'running', 'stopped', or 'unknown'
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0 and result.stdout.strip():
                if "Up" in result.stdout:
                    return "running"
                else:
                    return "stopped"
        except Exception:
            pass

        return "unknown"

    def populate_table(self):
        """Populate the DataTable with observatory services."""
        table = self.query_one("#observatory-table", DataTable)
        table.clear()

        if not self.services:
            table.add_row("○", "Observatory not configured", "--")
            return

        for idx, service in enumerate(self.services):
            # Status indicator
            if service['status'] == 'running':
                status = "●"  # Cyan (running)
            elif service['status'] == 'stopped':
                status = "○"  # Purple (idle)
            else:
                status = "⊗"  # Yellow (unknown)

            # Dashboard type
            dashboard = f"{service['type']}"
            if service['url']:
                dashboard += " [link]"

            table.add_row(
                status,
                service['name'],
                dashboard,
                key=str(idx)
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - open dashboard in browser."""
        try:
            row_key = event.row_key.value
            idx = int(row_key)
            service = self.services[idx]

            # Log to activity log
            log = self.app.query_one("#activity-log")
            timestamp = datetime.now().strftime('%H:%M:%S')

            if service['url']:
                log.write_line(f"[dim][{timestamp}][/dim] Opening: {service['name']}")
                self.open_url(service['url'])
                log.write_line(f"[green]✓[/green] Opened: {service['url']}")
            else:
                log.write_line(f"[yellow]⊗[/yellow] No URL configured for {service['name']}")

        except Exception as e:
            log = self.app.query_one("#activity-log")
            log.write_line(f"[red]✗[/red] Error opening dashboard: {e}")

    def open_url(self, url: str):
        """Open URL in default browser."""
        try:
            subprocess.Popen(
                ["open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            raise Exception(f"Could not open browser: {e}")

    def refresh_data(self):
        """Refresh observatory services."""
        self.load_observatory_config()
        self.populate_table()
