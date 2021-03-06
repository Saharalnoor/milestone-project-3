import os
import re
import math
from flask import Flask, render_template, request, url_for, flash, session, redirect
from flask_pymongo import PyMongo, pymongo
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from os import path
if path.exists("env.py"):
    import env

app = Flask(__name__)

app.config["MONGO_DBNAME"] = 'karaokean'
app.config["MONGO_URI"] = os.environ.get('MONGO_URI')
app.config["secret_key"] = os.environ.get('SECRET_KEY')

mongo = PyMongo(app)


@app.route('/')
def index():
    all_tracks = mongo.db.tracks
    tracks = all_tracks.find().sort('likes', pymongo.DESCENDING).skip(0).limit(5)
    return render_template("index.html", tracks=tracks)

# -------------------- LOGIN --------------------

@app.route('/login', methods=['GET','POST'])
def login():
    """  """
    if request.method == "POST":
        users = mongo.db.users
        login_user = users.find_one({'name': request.form['username']})
        """ Check that the username exists """
        if login_user:
            if check_password_hash(login_user['password'], request.form['password']):
                """ If password correct create session variable username and redirect to index """
                session['username'] = request.form['username']
                username = session["username"]
                flash("Kon'nichiwa " + username +  "!")                
                return redirect(url_for('index'))
            else:
                """ Password was incorrect"""
                flash("Password was incorrect")
            return redirect(url_for('login'))
        else:
            """Username doesn't exist in database """
            flash("Username doesn't exist")
            return redirect(url_for('login'))

        flash("Username doesn't exist")   
        return redirect(url_for('login'))
    return render_template('login.html')

# -------------------- LOGOUT --------------------

@app.route('/logout')
def logout():
    """ Sign out a user by using session.pop() """
    username = session["username"]
    flash("Sayōnara " + username)
    session.pop("username")
    return redirect(url_for("index"))


# -------------------- REGISTER --------------------
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name': request.form['username']})

        if existing_user is None:
            hashed_value = generate_password_hash(request.form['password'])
            users.insert(
                {'name': request.form['username'], 'password': hashed_value, 'playlist': []})
            session['username'] = request.form['username']
            username = session['username']
            flash("Welcome to Karaokean" + username + "!")
            return redirect(url_for('index'))

        username = request.form['username']
        flash("Username " + username + " already exists")
        return redirect(url_for('register'))
    
    return render_template('register.html')


@app.route('/addtrack')
def addtrack():
    genres = mongo.db.genre.find()
    return render_template('addtrack.html',genres=genres)


@app.route('/insert_track', methods=['POST'])
def insert_track():
    tracks = mongo.db.tracks
    video = request.form.get('video_link')
    new_track = request.form.get('track_name')
    # change string to lower case and them capitize the first letter of each word to compared to existing names in database without taking case into account
    track_title = new_track.lower().title()

    # Check if there is another track in the catalogue with the same name
    existing_track = mongo.db.tracks.find_one({'name': track_title})
    genre = request.form.get('genre_name')

    # Check URL for YouTube address characterists
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, video)

    sorting_order = 3 # load catalogue sorted by newest entry so user sees their update if successful 
    
    if existing_track is None: #If no other track with the same name exists
        try:
            tracks.insert_one(
                {
                    'name': track_title,
                    'artist': request.form.get('artist_name'),
                    'year': int(request.form.get('year')),
                    'genre': genre,
                    'lyrics': request.form.get('lyrics_link'),
                    'video': youtube_regex_match[6],
                    'likes': int(0),
                    'dislikes': int(0)
                }
            )
            flash("New song " + track_title + " added!")
            return redirect(url_for('catalogue', sorting_order=sorting_order))

        except:
            flash("Could not insert song")
    else:
        flash(track_title + " already exists in catalogue")
        return redirect(url_for('addtrack'))

    return redirect('addtrack')


@app.route('/edittrack/<track_id>/<page>/<sorting_order>')
def edittrack(track_id, page, sorting_order):
    the_track = mongo.db.tracks.find_one({"_id": ObjectId(track_id)})
    likes = int(the_track["likes"])
    dislikes = int(the_track["dislikes"])
    genres = mongo.db.genre.find()
    return render_template('edittrack.html', track=the_track, genres=genres, page=page, sorting_order=sorting_order, likes=likes, dislikes=dislikes)


@app.route('/update_track/<track_id>/<page>/<sorting_order>/<likes>/<dislikes>', methods=['POST'])
def update_track(track_id, page, sorting_order, likes, dislikes):
    tracks = mongo.db.tracks
    video = request.form.get('video_link')

    # Check URL for YouTube address characterists
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, video)   
    
    edit_track = request.form.get('track_name')

    # change string to lower case and them capitize the first letter of each word 
    track_title = edit_track.lower().title()
    try:
        tracks.update({'_id': ObjectId(track_id)},
            {
                'name': track_title,
                'artist': request.form.get('artist_name'),
                'year': int(request.form.get('year')),
                'genre': request.form.get('genre_name'),
                'lyrics': request.form.get('lyrics_link'),
                'video': youtube_regex_match[6],
                'likes': int(likes),
                'dislikes': int(dislikes)
            }
        )
        flash(track_title + " has been editted!")
        return redirect(url_for('catalogue', page=page, sorting_order=sorting_order))

    except:
        flash("Could not edit song")

    return redirect(url_for('catalogue', page=page, sorting_order=sorting_order))


@app.route('/delete_track/<track_id>/<page>/<sorting_order>')
def delete_track(track_id, page, sorting_order):
    the_track = mongo.db.tracks.find_one({"_id": ObjectId(track_id)})
    track_name = the_track["name"]
    flash(track_name + " deleted from catalogue")
    mongo.db.tracks.remove( {'_id': ObjectId(track_id)})
    return redirect(url_for('catalogue', page=page, sorting_order=sorting_order))


@app.route('/genre')
def genres():
    """ Template to see existing genres in database"""
    genres = mongo.db.genre.find()
    return render_template('genres.html', genres=genres)


@app.route('/addgenre')
def addgenre():
    """ Template to add new genre to database"""
    return render_template('addgenre.html')


@app.route('/insert_genre', methods=['POST'])
def insert_genre():
    """ Insert new genre to database"""
    genres = mongo.db.genre
    new_genre = request.form.get('genre_name')

    # change string to lower case and them capitize the first letter of each word to compared to existing names in database without taking case into account
    genre_title = new_genre.lower().title()
    existing_genres = mongo.db.genre.find_one({'name': genre_title})

    if existing_genres is None: # If there is no genre in the catalogue with the same names as that input
        try:
            genres.insert_one(
                {
                    'name': genre_title,
                }
            )
            flash("New genre " + genre_title + " added!")
            return redirect(url_for('genres'))
        except:
            flash("Could not insert genre")
    else:
        flash("Genre " + genre_title + " already exists")
        return redirect(url_for('addgenre'))

    return redirect(url_for('addgenre'))


@app.route('/editgenre/<genre_id>')
def editgenre(genre_id):
    the_genre = mongo.db.genre.find_one({"_id": ObjectId(genre_id)})
    return render_template('editgenre.html', genre=the_genre)


@app.route('/update_genre/<genre_id>', methods=['POST'])
def update_genre(genre_id):
    genres = mongo.db.genre
    edit_genre = request.form.get('genre_name')
    # change string to lower case and them capitize the first letter of each word to compared to existing names in database without taking case into account
    genre_title =  edit_genre.lower().title()
    existing_genres = mongo.db.genre.find_one({'name': genre_title}) #Check the new genre name is not already in database (this prevents duplicate genres)

    if existing_genres is None: # if no genre with the same name

        try:
            genres.update({'_id': ObjectId(genre_id)},
                {
                    'name': genre_title
                }
            )
            flash("Genre " + genre_title + " editted!")
            return redirect(url_for('genres'))

        except:
            flash("Could not edit genre")
    else:
        flash("Genre " + genre_title + " already exists")
        return redirect(url_for('editgenre',genre_id=genre_id))

    return redirect(url_for('editgenre',genre_id=genre_id))


@app.route('/catalogue/')
def catalogue():
    all_tracks = mongo.db.tracks
    tracks_total = all_tracks.count()
    args = request.args.get

    page_args = int(args("page")) if args(
        "page") else 0  # page_args are initial set to 0
    sorting_order = int(args("sorting_order")) if args("sorting_order") else 1
    limit_args = 5 # Limit of 5 tracks per page

    all_track_count = (range(1, (math.ceil(tracks_total / limit_args)) + 1))

    all_track_pages = []
    all_track_page_args = []

    for page in all_track_count:
        all_track_pages.append(page)
        p_args = (page*limit_args)-limit_args
        all_track_page_args.append(p_args)

    # ---------- SORTING ORDER ----------

    if sorting_order == 2:
        # Most Disliked Tracks
        tracks = all_tracks.find().sort('dislikes', pymongo.DESCENDING).skip(page_args).limit(limit_args)
    elif sorting_order == 3:
        # Date added Newest Tracks
        tracks = all_tracks.find().sort('_id', pymongo.DESCENDING).skip(page_args).limit(limit_args)
    elif sorting_order == 4:
        # Date added Oldest Tracks
        tracks = all_tracks.find().sort('_id', pymongo.ASCENDING).skip(page_args).limit(limit_args)
    else:
        # Most Liked Tracks
        tracks = all_tracks.find().sort('likes', pymongo.DESCENDING).skip(page_args).limit(limit_args)


    prev_url = page_args - limit_args
    next_url = page_args + limit_args

    return render_template('catalogue.html', tracks=tracks, tracks_total=tracks_total, page=page_args, prev_url=prev_url, next_url=next_url, all_track_pages_id=zip(all_track_pages, all_track_page_args), sorting_order=sorting_order)

@app.route('/sort_by_likes')
def sort_by_likes():
    """ Change sort order of Tracks on catalogue page to ASCENDING Likes """
    sorting_order = 1
    return redirect(url_for('catalogue', sorting_order=sorting_order))


@app.route('/sort_by_dislikes')
def sort_by_dislikes():
    """ Change sort order of Tracks on catalogue page to ASCENDING Dislikes """
    sorting_order = 2
    return redirect(url_for('catalogue', sorting_order=sorting_order))

@app.route('/sort_by_newest')
def sort_by_newest():
    """ Change sort order of Tracks on catalogue page to ASCENDING date added """
    sorting_order = 3
    return redirect(url_for('catalogue', sorting_order=sorting_order))

@app.route('/sort_by_oldest')
def sort_by_oldest():
    """ Change sort order of Tracks on catalogue page to DESCENDING date added """
    sorting_order = 4
    return redirect(url_for('catalogue', sorting_order=sorting_order))

@app.route('/playlist_addto/<track_id>', methods=['POST'])
def playlist_addto(track_id):
    """ Add the youtube_id of a video link to a list called playlist"""
    users = mongo.db.users
    username = session['username']

    the_user = users.find_one({"name": username})

    """
    It is not possible using pymongo to delete an entry in an array that is a document using just the array index. As this is the case, an array entry must be identified by it's content.

    The datestamp array parameter was added to the playlist array to provide a way to uniquely identify a song on a list that may have duplicates (i.e. The same song might appear multiple times on the playlist)

    It the array parameter was simply an increasing integer equal to the arrau index (1,2,3...) there may be times that due to deletions of first entries, the array might have the entries with the same parameters. This would mean that if the user made a request to delete one (i.e. calling the route/view) both entries would be deleted. Using the timestamp prevents this.

    """
    timestamp = datetime.now().strftime("%d-%m-%y-%H-%M-%S-%f")

    users.find_one_and_update(
        {"name": username}, {"$push": {'playlist': [timestamp, track_id]}})

    return redirect(url_for('catalogue'))


@app.route('/playlist_page')
def playlist_page():
    
    if 'username' in session:
        """ Show Users Playlist"""
        username = session['username']
        users = mongo.db.users
        the_user = users.find_one({"name": username})

        playlist_index = [] # list of timestamp index values from playlist array
        playlist_ids = [] # list of track track_id 
        playlist_names = [] # list of track song names

        playlist = the_user["playlist"]

        for playlist_id, track_id in the_user["playlist"]:
            the_track = mongo.db.tracks.find_one({"_id": ObjectId(track_id)})

            if the_track: # If track with id exists in the catalogue do not add to list
                playlist_index.append(playlist_id) # Add timestamp to playlist_index array
                playlist_ids.append(track_id) # Add track_id to playlist_ids array

                pl_name = the_track["name"]
                playlist_names.append(pl_name) # Add song name to playlist_names array
            else: # If no track with id in the catalogue do not add to list
                return redirect(url_for('playlist_delete', playlist_id=playlist_id, track_id=track_id))

        return render_template('playlist_page.html', users=users, playlist=playlist, playlist_names=zip( playlist_index, playlist_ids, playlist_names))
    else:
        return render_template('playlist_page.html')


@app.route('/playlist_play')
def playlist_play():
    
    if 'username' in session:
        """ Show Users Playlist"""
        username = session['username']
        users = mongo.db.users
        the_user = users.find_one({"name": username})

        playlist_ids = []
        playlist_index = []
        playlist_ytv = []
        playlist_names = []

        for playlist_id, track_id in the_user["playlist"]:
            playlist_index.append(playlist_id) # Add timestamp to playlist_index array
            playlist_ids.append(track_id)  # Add track_id to playlist_ids array

            the_track = mongo.db.tracks.find_one({"_id": ObjectId(track_id)})
            ytv = the_track["video"]
            playlist_ytv.append(ytv) # Add YouTube video link if to playlist_ytv array

            pl_name = the_track["name"]
            playlist_names.append(pl_name) # Add song name to playlist_names array

        return render_template('playlist_play.html', users=the_user, playlist=playlist_ytv, playlist_id=playlist_index, playlist_names=zip(playlist_index, playlist_ids, playlist_names))
    else:
        return render_template('playlist_play.html')

        
@app.route('/playlist_delete/<playlist_id>/<track_id>')
def playlist_delete(playlist_id,track_id):
    """ Delete the _id of a video link from the array playlist in the database"""
    users = mongo.db.users
    username = session['username']

    """find and remove ($pull) array entry with both($all) the correct playlist_id and track_id"""
    users.find_one_and_update({"name": username},
    {"$pull": {'playlist': { "$all":[playlist_id, track_id]} }})  

    return redirect(url_for('playlist_page'))

@app.route('/like/<track_id>', methods=['POST'])
def like(track_id):
    tracks = mongo.db.tracks
    """Find correct track and increase Likes by 1"""
    tracks.find_one_and_update(
        {"_id": ObjectId(track_id)}, {"$inc": {'likes': 1}})

    return redirect(url_for('catalogue'))


@app.route('/dislike/<track_id>', methods=['POST'])
def dislike(track_id):
    tracks = mongo.db.tracks

    """Find correct track and increase Dislikes by 1"""
    tracks.find_one_and_update({"_id": ObjectId(track_id)}, {
                               "$inc": {'dislikes': 1}})

    return redirect(url_for('catalogue'))

# ---------- Error Handlers ----------

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404

@app.errorhandler(500)
def page_not_found(error):
    return render_template('error.html'), 500

@app.errorhandler(HTTPException)
def handle_exception(e):
    response = e.get_response()
    return render_template('error.html'), response

if __name__ == '__main__':
    app.secret_key = 'secret_key'
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')))
