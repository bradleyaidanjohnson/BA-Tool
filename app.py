from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from models import db, Project, Feature, UserStory, Attachment, Personnel, Note
import os
from werkzeug.utils import secure_filename
from utils.word_export import export_feature_to_docx, Document, add_table_of_contents
import io
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_data.db'
app.config['SQLALCHEMY_TRACK MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'xlsx', 'csv'}
db.init_app(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def build_feature_breadcrumbs(feature):
    breadcrumbs = []
    current = feature
    while current:
        breadcrumbs.append(current)
        current = current.parent  # assuming your Feature model has this relationship
    breadcrumbs.reverse()
    return breadcrumbs


@app.route('/')
def index():
    projects = Project.query.all()
    return render_template('index.html', projects=projects)

@app.route('/project/new', methods=['GET', 'POST'])
def new_project():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        project = Project(name=name, description=description)
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('project_form.html')

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('project_form.html', project=project)

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/project/<int:project_id>')
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    show_added = request.args.get('show_added', '1') == '1'
    return render_template('project_details.html', project=project, show_added=show_added)

@app.route('/feature/<int:feature_id>')
def view_feature(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    show_added = request.args.get("show_added", "1") == "1"
    breadcrumbs = build_feature_breadcrumbs(feature)
    return render_template(
        "feature_details.html",
        feature=feature,
        show_added=show_added,
        breadcrumbs=breadcrumbs, root_feature=feature
    )

@app.route('/project/<int:project_id>/feature/new', methods=['GET', 'POST'])
@app.route('/project/<int:project_id>/feature/<int:parent_id>/child', methods=['GET', 'POST'])
def new_feature(project_id, parent_id=None):
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        feature = Feature(title=title, description=description, project_id=project_id, parent_feature_id=parent_id)
        db.session.add(feature)
        db.session.commit()
        return redirect(url_for('view_project', project_id=project_id))
    return render_template('feature_form.html', project_id=project_id, parent_id=parent_id)

@app.route('/feature/<int:feature_id>/edit', methods=['GET', 'POST'])
def edit_feature(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    if request.method == 'POST':
        feature.title = request.form['title']
        feature.description = request.form['description']
        db.session.commit()
        return redirect(url_for('view_feature', feature_id=feature.id))
    
    return render_template('feature_form.html', feature=feature, project_id=feature.project_id)


@app.route('/feature/<int:feature_id>/story/new', methods=['GET', 'POST'])
def new_story(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    personnel = Personnel.query.order_by(Personnel.name).all()

    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        created_by_id = request.form.get("created_by_id")

        story = UserStory(
            feature_id=feature.id,
            title=title,
            details=details,
            created_by_id=int(created_by_id) if created_by_id else None
        )
        db.session.add(story)
        db.session.flush()  # Ensure story.id is available before adding attachments

        # Handle file uploads
        files = request.files.getlist('attachments')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                attachment = Attachment(filename=filename, story=story)
                db.session.add(attachment)

        # Optional: handle notes on creation (can skip this if you prefer to only add on edit)
        note_details = request.form.getlist("note_details[]")
        personnel_ids = request.form.getlist("personnel_id[]")
        for details, personnel_id in zip(note_details, personnel_ids):
            if details.strip() and personnel_id:
                note = Note(
                    story=story,
                    content=details.strip(),
                    personnel_id=int(personnel_id),
                    created_at=datetime.utcnow()
                )
                db.session.add(note)

        db.session.commit()
        return redirect(url_for('view_project', project_id=feature.project_id))

    return render_template('story_form.html', feature=feature, personnel=personnel)


# @app.route('/story/<int:story_id>/edit', methods=['GET', 'POST'])
# def edit_story(story_id):
#     story = UserStory.query.get_or_404(story_id)
#     if request.method == 'POST':
#         story.title = request.form['title']
#         story.details = request.form['details']
#         story.created_by = request.form['created_by']

#         # Handle file uploads
#         files = request.files.getlist('attachments')
#         for file in files:
#             if file and allowed_file(file.filename):
#                 filename = secure_filename(file.filename)
#                 file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 file.save(file_path)
#                 attachment = Attachment(filename=filename, story=story)
#                 db.session.add(attachment)

#         db.session.commit()
#         return redirect(url_for('view_project', project_id=story.feature.project_id))
#     return render_template('story_form.html', feature=story.feature, story=story)

@app.route("/story/<int:story_id>/edit", methods=["GET", "POST"])
def edit_story(story_id):
    story = UserStory.query.get_or_404(story_id)
    personnel = Personnel.query.order_by(Personnel.name).all()

    if request.method == "POST":
        story.title = request.form['title']
        story.details = request.form['details']
        created_by_id = request.form.get("created_by_id")
        if created_by_id:
            story.created_by_id = int(created_by_id)

        # Handle file uploads
        files = request.files.getlist('attachments')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                attachment = Attachment(filename=filename, story=story)
                db.session.add(attachment)
        # Update story details (e.g., story.details = request.form["details"])
        # Add new notes
        note_details = request.form.getlist("note_details[]")
        personnel_ids = request.form.getlist("personnel_id[]")

        notes_added = False
        for details, personnel_id in zip(note_details, personnel_ids):
            if details.strip() and personnel_id:
                new_note = Note(
                    story_id=story.id,
                    details=details.strip(),
                    personnel_id=int(personnel_id),
                    created_at=datetime.utcnow()
                )
                db.session.add(new_note)
                notes_added = True
        if notes_added:
            story.ado_added = False
        db.session.commit()
        return redirect(url_for("edit_story", story_id=story.id))

    return render_template("story_form.html", story=story, personnel=personnel, feature=story.feature)


@app.route('/story/<int:story_id>/delete', methods=['POST'])
def delete_story(story_id):
    story = UserStory.query.get_or_404(story_id)
    project_id = story.feature.project_id
    db.session.delete(story)
    db.session.commit()
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/attachment/<int:attachment_id>/delete', methods=['POST'])
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)

    # Delete File from disk if it exists
    if os.path.exists(file_path):
        os.remove(file_path)

    story = attachment.story
    db.session.delete(attachment)
    db.session.commit()

    # return redirect(url_for('edit_story', story_id=story.id))
    return '', 204  # No content, just refresh

@app.route('/story/<int:story_id>/toggle_ado', methods=['POST'])
def toggle_ado(story_id):
    story = UserStory.query.get_or_404(story_id)
    story.ado_added = not story.ado_added
    db.session.commit()
    return jsonify({'status': 'success', 'ado_added': story.ado_added})

@app.route('/project/<int:project_id>/export_stories')
def export_stories(project_id):
    project = Project.query.get_or_404(project_id)
    
    def gather_stories(feature):
        stories = [s for s in feature.user_stories if not s.ado_added]
        for sub in feature.subfeatures:
            stories.extend(gather_stories(sub))
        return stories
    
    all_stories = []
    for feature in project.features:
        all_stories.extend(gather_stories(feature))

    return render_template('export_stories.html', stories=all_stories, project=project)

@app.route('/feature/<int:feature_id>/export_stories')
def export_feature_stories(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    
    def gather_stories(f):
        stories = [s for s in f.user_stories if not s.ado_added]
        for sub in f.subfeatures:
            stories.extend(gather_stories(sub))
        return stories
    
    stories = gather_stories(feature)

    return render_template('export_stories.html', stories=stories, project=feature.project)


@app.route('/project/<int:project_id>/export_word')
def export_project_word(project_id):
    project = Project.query.get_or_404(project_id)
    doc = Document()
    doc.add_heading(f"Project: {project.name}", 0)
    add_table_of_contents(doc)

    personnel_set = set()

    for i, feature in enumerate(project.features, start=1):
        if not feature.parent_feature_id:
            export_feature_to_docx(
                feature, 
                numbering=[i], 
                doc=doc, 
                include_notes=True,  # Set to False to omit notes
                personnel_set=personnel_set
            )

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{project.name}_export.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@app.route('/feature/<int:feature_id>/export_word')
def export_feature_word(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    personnel_set = set()
    doc = export_feature_to_docx(
        feature,
        numbering=[1],
        doc=None,
        include_notes=True,  # Set to False to skip notes
        personnel_set=personnel_set
    )

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{feature.title}_export.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@app.route('/personnel/add', methods=['GET', 'POST'])
def add_personnel():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        scope = request.form['scope']

        new_person = Personnel(name=name, email=email, role=role, scope=scope)
        db.session.add(new_person)
        db.session.commit()
        return redirect(url_for('list_personnel'))
    
    return render_template('add_personnel.html')

@app.route('/personnel/search')
def search_personnel():
    term = request.args.get('term', '')
    results = Personnel.query.filter(Personnel.name.ilike(f"%{term}%")).all()
    return jsonify([{'id': p.id, 'label': p.name, 'value':p.name} for p in results])

@app.route('/personnel')
def list_personnel():
    personnel = Personnel.query.order_by(Personnel.name).all()
    return render_template('list_personnel.html', personnel=personnel)

@app.route('/personnel/<int:personnel_id>/edit', methods=['GET', 'POST'])
def edit_personnel(personnel_id):
    person = Personnel.query.get_or_404(personnel_id)
    if request.method == 'POST':
        person.name = request.form['name']
        person.email = request.form['email']
        person.role = request.form['role']
        person.scope = request.form['scope']
        db.session.commit()
        return redirect(url_for('list_personnel'))
    return render_template('add_personnel.html', person=person)

@app.route('/personnel/<int:personnel_id>/delete', methods=['POST'])
def delete_personnel(personnel_id):
    person = Personnel.query.get_or_404(personnel_id)
    db.session.delete(person)
    db.session.commit()
    return redirect(url_for('list_personnel'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)