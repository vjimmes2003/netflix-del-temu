from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


def admin_required(view):
    """Limita una ruta a usuarios administradores."""

    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view


@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")