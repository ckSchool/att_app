import os

from flask import Flask, Response
from flask import flash, redirect, render_template, request, url_for
from flask import session, abort, jsonify

import datetime
import json
import mysql.connector as sql_conn
import secret

import fetch

app = Flask(__name__)

# global variables
db = ''
cursor = ''
connected_to = ''
user_id = ''
group_yr_yr = 2018
groupType_colours = {'excur': (.6, .8, .5, 1),
                      'formclass': (.9, .8, .7, 1),
                      'moving': (.7, .8, .9, 1),
                      'lesson': (.9, .7, .8, 1),
                      'own': (.7, .9, .8, 1)}
all_my_groups = {}
groupsList = {}
fetch.connection()


@app.route('/')
def home():
    global groupsList, all_my_groups
    if not session.get('logged_in'):
        return render_template('login.html')

    else:
        all_my_groups = fetch.all_groups(user_id, group_yr_yr)
        groupsList = fetch.groups_list(user_id, group_yr_yr)
        return render_template('groups.html', user=user_id, groups=groupsList)


@app.route('/groupMembers/<int:group_id>')
def groupMembers(group_id):
    print('selected group_id', group_id)

    selected_group = all_my_groups[group_id]
    print('selected_group:', selected_group)

    background_colour = selected_group['background_colour']
    date = '2018-11-22'
    members = fetch.get_members_for_group(selected_group, date)
    group_type = selected_group['group_type']

    last_att_today = ()
    group_name = selected_group['group_name']
    # ({f_att}}{{g_att}}

    if group_type =='formclass':
        return render_template('groupMembersHead.html', members=members, last_att_today=last_att_today, group_id=group_id, group_name=group_name, background_colour=background_colour)

    else:
        return render_template('groupMembers.html', members=members, last_att_today=last_att_today, group_id=group_id, group_name=group_name, background_colour=background_colour)
 
# @app.route('/groupMembers/<int:group_id>', methods=['POST'])
#
# # your code
# attendance = request.form['attendance']
# # return a response
# return



@app.route('/memberDetails/<member_id>')
def memberDetails(member_id):
    return render_template('memberDetails.html', member_id=member_id)#, background_colour=background_colour)

@app.route('/groupDetails/<int:group_idx>')
def groupDetails(group_idx):
    g=all_my_groups[group_idx]
    return render_template('groupDetails.html', group=g['title'])#, background_colour=background_colour)

user = {}



@app.route('/login', methods=['POST'])
def do_admin_login():
    global user_id, user
    password = request.form['password']
    user_id = request.form['username']
    user = fetch.user(user_id, password)
    if user:
        session['logged_in'] = True
    else:
        flash('wrong password!')
    return home()


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True, host='127.0.0.1', port=3000)