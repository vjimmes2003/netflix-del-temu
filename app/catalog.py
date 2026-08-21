from flask import Blueprint, render_template
from flask_login import login_required


catalog_bp = Blueprint("catalog", __name__)


@catalog_bp.route("/catalog")
@login_required
def catalog():
    return render_template("catalog.html")