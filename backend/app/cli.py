"""Command-line setup commands:  flask --app run <command>"""
import secrets
from datetime import timedelta

import click

from app.extensions import db
from app.models import Project, Task, User, utcnow


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables (safe to run again)."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option(help="At least 10 characters, with a letter and a number.")
    def create_admin(name, email, password):
        """Create the first admin account (you choose the password; none is built in)."""
        import re
        email = email.strip().lower()
        if len(password) < 10 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise click.ClickException("Password must be 10+ characters with a letter and a number.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("A user with this email already exists.")
        user = User(name=name.strip(), email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin created: {email}")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Create DEMO users, a project and sample tasks. DEMO DATA ONLY: delete before deployment."""
        admin = User.query.filter_by(role="admin").first()
        if admin is None:
            raise click.ClickException("Create an admin first: flask --app run create-admin")
        if User.query.filter_by(email="demo.manager@example.com").first():
            raise click.ClickException("Demo data already exists.")
        password = "Demo" + secrets.token_hex(5) + "9"
        manager = User(name="Demo Manager", email="demo.manager@example.com", role="manager")
        manager.set_password(password)
        db.session.add(manager)
        db.session.flush()
        emps = []
        for n, e in (("Demo Employee One", "demo.employee1@example.com"), ("Demo Employee Two", "demo.employee2@example.com")):
            u = User(name=n, email=e, role="employee", manager_id=manager.id)
            u.set_password(password)
            db.session.add(u)
            emps.append(u)
        project = Project(name="Demo Project", description="Sample data for demonstration", created_by=admin.id)
        db.session.add(project)
        db.session.flush()
        project.members = [manager] + emps
        today = utcnow().date()
        samples = [  # title, assignee idx, priority, status, progress, start offset, deadline offset, est hours, rejects, last update days ago
            ("Design login page", 0, "High", "In Progress", 40, -10, 2, 16, 0, 6),
            ("Write API documentation", 0, "Medium", "In Progress", 70, -8, 9, 10, 1, 1),
            ("Set up database backup", 1, "Critical", "Pending", 0, -2, 3, 12, 0, 2),
            ("Fix report export bug", 1, "High", "Blocked", 20, -6, -1, 8, 2, 8),
            ("Prepare test plan", 0, "Low", "Under Review", 95, -14, 5, 6, 0, 0),
            ("Create user guide", 1, "Medium", "Completed", 100, -20, -5, 10, 0, 0),
            ("Refactor dashboard code", 1, "Medium", "In Progress", 55, -7, 12, 20, 0, 2),
            ("Review security checklist", 0, "High", "In Progress", 15, -3, 4, 14, 0, 4),
        ]
        for title, i, prio, status, prog, s_off, d_off, est, rej, ago in samples:
            t = Task(title=title, description="Demo task", project_id=project.id, assignee_id=emps[i].id,
                     manager_id=manager.id, priority=prio, status=status, progress=prog,
                     start_date=today + timedelta(days=s_off), deadline=today + timedelta(days=d_off),
                     estimated_hours=est, actual_hours=round(est * prog / 100, 1), rejection_count=rej,
                     last_progress_update=utcnow() - timedelta(days=ago), created_by=manager.id,
                     completed_at=utcnow() - timedelta(days=3) if status == "Completed" else None)
            db.session.add(t)
        db.session.commit()
        click.echo("DEMO data created. Log in with these accounts (all share this password):")
        click.echo("  demo.manager@example.com, demo.employee1@example.com, demo.employee2@example.com")
        click.echo(f"  Password: {password}")
        click.echo("Delete or deactivate these accounts before any real deployment.")

    @app.cli.command("train-model")
    def train_model():
        """Train the delay-risk model on SYNTHETIC data and save it."""
        from app.ai.train import train
        meta = train()
        click.echo(f"Saved {meta['model_version']} (trained on synthetic data).")
        click.echo("Metrics (synthetic held-out data, NOT real-world accuracy):")
        for key, value in meta["metrics"].items():
            click.echo(f"  {key}: {value}")
