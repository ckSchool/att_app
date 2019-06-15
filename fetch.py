import os

from flask import Flask, Response
from flask import flash, redirect, render_template, request, url_for
from flask import session, abort, jsonify

import datetime
import json
import mysql.connector as sql_conn
import secret

app = Flask(__name__)

# global variables
db = ''
cursor = ''
connected_to = ''
user_id = ''
connected = False

sch_yr = 2018
groupType_colours = {'excur': (.6, .8, .5, 1),
                      'formclass': (.9, .8, .7, 1),
                      'moving': (.7, .8, .9, 1),
                      'lesson': (.9, .7, .8, 1),
                      'own': (.7, .9, .8, 1)}


groupType_colours = { 'excur': "#559bbb",
                      'formclass': "#559cec",
                      'moving': "#46c9cc",
                      'lesson': "#4b44a3",
                      'own': "#4b24a3"  }

all_my_groups = {}
groupsList = {}
user = {}


def conn_lan():
    try:
        db = sql_conn.connect(**secret.config_local)
        return db
    except:
        print('no local network connection')


def conn_remote():
    try:
        db = sql_conn.connect(**secret.config_remote)
        cursor = db.cursor(dictionary=True)
    except:
        print('no remote network connection')


def connect_to_thisdell():
    global db, cursor, connected_to, connected
    try:
        db = sql_conn.connect(**secret.thisdell)
        cursor = db.cursor(dictionary=True)
        connected = True
        connected_to = 'remote'
        print('CONNECTED to thisdell')
        return True, True
    except:
        print('no connection to:(', config)


def connection():
    global db, cursor, connected_to, connected
    retried = 0
    connected = False
    while not connected:
        retried += 1
        try:
            db = sql_conn.connect(**secret.config_local)  # config_local)
            cursor = db.cursor(dictionary=True)
            connected = True
            connected_to = 'local'
            return True, True
        except Exception as e:
            print('Could not connect to config_local')
            try:
                print()
                print('trying to connect to config_remote')
                db = sql_conn.connect(**secret.config_remote)
                cursor = db.cursor(dictionary=True)
                connected = True
                connected_to = 'remote'
                print('CONNECTED to config_remote')
                return True, True
            except Exception as e:
                print(e)
                print('Check internet connection')
        #
        if retried > 9:
            print('Retried 10 times, please check network connection')
            return False, False
    pass


def sq_all(sql):
    try:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()
        return res

    except Exception as e:
        print(e)
        connection()

    if db:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()
        return res
    else:
        return ''


def sq_single(sql):
    try:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchone()
        cur.close()
        return res
    except Exception as e:
        print(e)
        connection()

    if db:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchone()
        cur.close()
        return res
    else:
        return ''


def groups_list(user_id, sch_yr):
    global all_my_groups
    groupsList = []
    all_my_groups = all_groups(user_id, sch_yr)
    if all_my_groups:
        for idx in all_my_groups:
            group = all_my_groups[idx]

            # group  {'group_type': 'lesson', 'sch_div': 'smp', 'title': 'Design and Technology', 
            # 'subtitle': '7 A', 'background_colour': '#4b44a3', 'kelas_id': 'KLS001', 
            # 'pelajaran_id': 'bDT00007', 'group_name': 'Design and Technology', 
            # 'joined_classes': [], 'instructor_id': 's0103', 'notes': 'notes', 'days': ''}

            print("group ",group)
            groupsList.append([idx, group['title'], group['subtitle'], group['background_colour']])
    return groupsList


def all_groups(teacher_id, sch_yr):
    groups = {}
    groups.update(formclasses(len(groups), teacher_id, sch_yr))
    groups.update(lessons(len(groups), teacher_id, sch_yr))
    groups.update(excuric(len(groups), teacher_id, sch_yr))
    return groups


def formclasses(idx, guru_id, sch_yr):
    formclasses = all_teachers_formclasses(guru_id, sch_yr)
    formclassesList = {}

    # repack the data
    for formclass in formclasses:
        print('formclass', formclass)

        sch_div = formclass['div']
        subtitle = formclass[1]

        # create unique id for this group
        group_name = "Formclass:%s" % subtitle
        background_colour = groupType_colours['formclass']
        print('formclass background_colour', background_colour)
        notes = 'notes'
        daynumbers = ""

        group_data = dict(group_type ='formclass',
                          sch_div = sch_div,
                          title = 'formclass',
                          subtitle = subtitle,
                          background_colour = background_colour,
                          kelas_id = classdata[0],
                          pelajaran_id='',
                          group_name = group_name,
                          joined_classes = [],
                          instructor_id = guru_id,
                          notes = notes,
                          days=daynumbers)

        # add data object to list
        formclassesList[idx] = group_data
        idx += 1

    return formclassesList


def lessons(idx, guru_id, sch_yr):
    # collect date for group_types 'lesson:', 'moving', 'own'

    lessonsList = {}

    lessons = all_teachers_lessons(guru_id, sch_yr)  # flask

    for lesson in lessons:
        sch_div = lesson['sch']
        title = lesson['pelajaran_nama']
        kelas_id = lesson['kelas_id']
        subject_id = lesson['pelajaran_id']
        joined_classes = []

        if kelas_id[:2] == "MC":
            group_type = 'moving'
            joined_classes = joint_formclass_ids(sch_div, kelas_id)
            subtitle = 'xyz'  # _classes_linked_to_movingclass(sch_div, kelas_id)  # flask

        else:
            subtitle = formclass_nickname(sch_div, kelas_id)  # flask
            if is_this_teachers_formclass(sch_div, kelas_id, guru_id):  # flask
                group_type = 'own'
                
            else:
                group_type = 'lesson'

        background_colour = groupType_colours[group_type]
        print("lesson colour", background_colour)

        notes = 'notes'
        daynumbers=""

        group_data = dict(group_type=group_type,
                          sch_div=sch_div,
                          title=title,
                          subtitle=subtitle,
                          background_colour=background_colour,
                          kelas_id=kelas_id,
                          pelajaran_id=subject_id,
                          group_name=title,
                          joined_classes=joined_classes,
                          instructor_id=guru_id,
                          notes = notes,
                          days=daynumbers)

        lessonsList[idx] = group_data
        idx += 1

    return lessonsList



def excuric(idx, teacher_id, sch_yr):
    excurList = {}
    excur_groups = teachers_excur(teacher_id, sch_yr)  

    for excur in excur_groups:
        kelas_id = excur['kelas_id']
        title = excur['group_name']

        daynumbers = excur['days'].split(',')
        days = daynumbers_to_daynames(daynumbers)

        sch_div= excur['div']

        subtitle = 'excul %s: %s ' % (sch_div, days)

        background_colour = groupType_colours['excur']
        print(background_colour)
        notes = 'notes'

        group_data = dict(group_type='excur',
                          sch_div=sch_div,
                          title=title,
                          subtitle=subtitle,
                          background_colour=background_colour,
                          kelas_id=kelas_id,
                          pelajaran_id = '',
                          group_name=title,
                          joined_classes=[],
                          instructor_id=guru_id,
                          notes=notes,
                          days=daynumbers)

        excurList[idx] = group_data
        idx += 1

    return excurList



def joint_formclass_ids(sch_div, movingclass_id):
    formclass_ids_list = []
    sql = "SELECT class_ids \
                 FROM all_movingclasses \
                WHERE sch='%s' AND kelas_id = '%s' " % (sch_div, movingclass_id)
    res = flask_single_plain(sql)
    if not res:
        return formclass_ids_list

    class_ids = res['class_ids']
    if not class_ids:
        return formclass_ids_list

    formclass_ids = class_ids.split(',')
    if formclass_ids:
        for formclass_id in formclass_ids:
            formclass_ids_list.append(formclass_id)

    return formclass_ids_list


def daynumbers_to_daynames(daynumbers=[]):
    daynames = []
    for no in daynumbers:
        daynames.append('')
    return daynames

def user(user_id, password):
    sql = "SELECT * FROM se_user \
                WHERE user_id = '%s' \
                  AND user_pwd = PASSWORD('%s')" % (user_id, password)
    cursor.execute(sql)
    xuser = cursor.fetchone()
    print('user:', xuser)
    return xuser

def all_teachers_formclasses(guru_id, sch_yr):
    mylist = []
    sql = "SELECT * FROM all_formclasses WHERE guru_id = '%s'"

    res = flask_all_plain(sql)
    if res:
        for row in res:
            row_data = [row['kelas_id'], row['kelas_nama_lain'], row['sch'], 'formclasses']
            mylist.append(row_data)
    return mylist


def teachers_lessons(sch_div, teacher_id, sch_yr):
    lessons_list = []
    sql = "SELECT p.pelajaran_id, p.pelajaran_nama, \
                  gd.guru_pelajaran_kelas_id  AS kelas_id \
             FROM tblgurudetil%s gd \
             JOIN tblpelajaran%s p ON gd.guru_pelajaran_id = p.pelajaran_id \
            WHERE gd.guru_id = '%s' \
            ORDER BY p.pelajaran_nama" % (sch_div, sch_div, teacher_id)
    res = flask_all_plain(sql)
    try:
        lessons_list = [row for row in res]
    except Exception as e:
        print(e)
    return lessons_list


def all_teachers_lessons(guru_id, sch_yr):
    lessons_list = []
    sql = "SELECT * FROM all_lessons WHERE guru_id = '%s'" % (guru_id,)
    res = flask_all_plain(sql)
    try:
        lessons_list = [row for row in res]
    except Exception as e:
        print(e)
    return lessons_list


def flask_all_plain(sql):
    # print(sql)
    try:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()
        return res

    except Exception as e:
        print(e)
        connection()

    if db:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()
        return res
    else:
        return ''


def flask_single_item(sql, item, elsestr):
    try:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchone()
        cur.close()
        return res
    except Exception as e:
        print(e)
        connection()

    if db:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchone()
        cur.close()
        try:
            if res:
                item = res[item]
                if item:
                    return item
                else:
                    return elsestr
            else:
                return elsestr
        except Exception as e:
            print(e)
            return elsestr
    else:
        return elsestr


def flask_single_plain(sql):
    try:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchone()
        cur.close()
        return res
    except Exception as e:
        print(e)
        connection()

    if db:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        res = cur.fetchone()
        cur.close()
        return res
    else:
        return ''


def flask_post(sql):
    # print('post ', sql)
    try:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        db.commit()

    except Exception as e:
        print(e)
        connection()

    if db:
        cur = db.cursor(dictionary=True)
        cur.execute(sql)
        db.commit()
    else:
        return ''


def teachers_excur(teacher_id, sch_yr):
    lessons_list = []
    sql = "SELECT * \
             FROM all_excur \
            WHERE guru_pelajaran_kelas_id = '-' \
              AND guru_id = '%s'" % (teacher_id,)
    res = flask_all_plain(sql)
    if res:
        lessons_list = [row for row in res]

    return lessons_list


def is_this_teachers_formclass(sch_div, kelas_id, teacher_id):
    sql = "SELECT guru_id FROM all_walikelas \
            WHERE sch='%s' AND guru_id = '%s' AND guru_wali_kelasid='%s'" % (sch_div, teacher_id, kelas_id)
    res = flask_single_plain(sql)
    if res:
        return True
    else:
        return False


def formclass_nickname(sch_div, kelas_id):
    sql = "SELECT kelas_nama_lain FROM tblkelas%s \
            WHERE kelas_id='%s'" % (sch_div, kelas_id)
    res = flask_single_plain(sql)
    if not res:
        nickname = ''
    else:
        nickname = res['kelas_nama_lain']
    return nickname


def get_members_for_group(groupData, date):

    members = []

    print('get_members_for_group:', groupData, date)
    # {'sch_div': 'smp',
    # 'kelas_id': 'KLS003',
    # 'pelajaran_id': 'bDT00007',
    # 'group_name': 'Design and Technology',
    # 'group_type': 'lesson',
    # 'joined_classes': [],
    # 'instructor_id': 's0103'}

    sch_div = groupData['sch_div']
    kelas_id = groupData['kelas_id']
    subject_id = groupData['pelajaran_id']
    group_name = 'group_name'
    group_type = groupData['group_type']
    joined_classes = groupData['joined_classes']
    instructor_id = groupData['instructor_id']



    att_data = {}

    print('group_type',group_type)

    if group_type == 'moving':
        att_data = _moving_att(sch_yr, date, sch_div, kelas_id, subject_id)

    elif group_type == 'lesson':

        print('get members for l:', sch_yr, date, sch_div, subject_id, kelas_id)

        att_data = _lesson_att(sch_yr, date, sch_div, subject_id, kelas_id)


    elif group_type == 'excur':
        att_data = _excur_att(sch_yr, date, sch_div, kelas_id)

    elif group_type == 'formclass' or group_type == 'own':
        att_data = _form_att(sch_yr, date,  sch_div, kelas_id)


    timestamp = att_data['timestamp'] # {'absen_timestamp': datetime.datetime(2018, 11, 22, 10, 9, 50)}

    members = att_data['members']

    print('att_data:', timestamp)

    member_list = []
    for member_id in members:
        member = members[member_id]

        # 'P1037': {'siswa_nopin': 'P1037', 'siswa_nama_lengkap': 'Andrian Hindra', 'f_att': '-',
        #  'formclass_id': 'KLS003', 'group_type': 'lesson', 'sch_div': 'smp', 'g_att': '-'}
        print(member_id, member)
        member_name = member['siswa_nama_lengkap']
        f_att = member['f_att']
        g_att = member['g_att']

        img_path = "http://192.168.0.254/smsicons"
        img_url = "%s/%s/%s.jpg" % (img_path, sch_div, member_id)

        member_list.append((member_id, member_name, f_att, g_att, img_url))

    return member_list


def time_lesson_g_att_taken(sch_div, absent_id):
    sql = "SELECT absen_timestamp FROM siswa_absenhead%s \
                           WHERE absen_id = '%s'" % (sch_div, absent_id)
    return flask_single_item(sql, 'absen_timestamp', '')


def time_f_att_taken(formclass_id, date, sch_div):
    sql = "SELECT timestamp FROM ck_absen_head \
            WHERE group_type = 'formclass' \
              AND sch_div = '%s' \
              AND class_id ='%s' \
              AND date ='%s' " % (sch_div, formclass_id, date)
    return flask_single_item(sql, 'timestamp', '')


def _form_att(sch_yr, date, sch_div, formclass_id):
    # sch_div = lesson_data['sch_div']
    # formclass_id = lesson_data['kelas_id']

    # if sch_div == 'sma': sch_div = 'smu'

    absence_taken = time_f_att_taken(formclass_id, date, sch_div)
    member_list = _formclass_att_core(sch_div, sch_yr, date, formclass_id)
    att_dict = {}
    for member in member_list:
        member_id = member['siswa_nopin']
        member['group_type'] = 'formclass'
        member['lesson_id'] = formclass_id
        member['sch_div'] = sch_div
        # Only non attendance is recorded otherwise regard as in attendance
        if absence_taken:
            if not member['f_att']:
                member['f_att'] = 'H'
        else:
            member['f_att'] = 'H'
        # put data back into dict
        att_dict[member_id] = member
    return {'timestamp': absence_taken, 'members': att_dict}


def _formclass_att_core(sch_div, sch_yr, date, formclass_id):
    # sql = "SELECT siswa_nopin, siswa_nama_lengkap, f_att, formclass_id \
    #          FROM formclass_att_core \
    #         WHERE sch = '%s' \
    #           AND klapper_tahun_ajaran = %d \
    #           AND absen_tanggal = '%s' \
    #           AND klapper_kelas_id = '%s' \
    #         ORDER BY siswa_nama_lengkap " % (sch_div, int(sch_yr), date,  formclass_id)
    sql = "SELECT s.siswa_nopin, s.siswa_nama_lengkap, a.absen_status AS f_att, \
                      sk.klapper_kelas_id AS formclass_id \
                 FROM siswa_%s s  JOIN siswa_klapper%s sk \
                   ON sk.klapper_siswa_nopin = s.siswa_nopin \
            LEFT JOIN siswa_absen%s a \
                   ON a.absen_kelas_id = sk.klapper_kelas_id \
                  AND a.absen_siswa_nopin= s.siswa_nopin \
                  AND a.absen_tanggal = '%s' \
                WHERE sk.klapper_tahun_ajaran = %d \
                  AND sk.klapper_kelas_id = '%s' \
                ORDER BY s.siswa_nama_lengkap " % (sch_div, sch_div, sch_div,
                                                   date, int(sch_yr), formclass_id)
    return flask_all_plain(sql)
    return flask_all_plain(sql)


def _lesson_att(sch_yr, date, sch_div, subject_id, formclass_id):

    absent_id = "%s%s%s%s" % (date, subject_id, formclass_id, user_id.lower())
    print(' absent_id :', absent_id)

    absence_taken = time_lesson_g_att_taken(sch_div, absent_id)
    print('absence_taken:', absence_taken)


    # get list of members for formclass + their morning attendance, if any
    member_list = _formclass_att_core(sch_div, sch_yr, date, formclass_id)
    print('_formclass_att_core . member_list:', member_list)


    # add lesson lesson attendance (g_att) to each member
    absent_id = "%s%s%s" % (date, sch_div, subject_id)
    att_dict = {}
    for member in member_list:
        member_id = member['siswa_nopin']
        member['group_type'] = 'lesson'
        member['sch_div'] = sch_div

        if not member['f_att']:
            member['f_att']='-'

        # get attendance for lesson
        if absence_taken:
            ab = g_att_lesson(member_id, sch_div, absent_id, absence_taken)
            if ab:
                member['g_att'] = ab
            else:
                member['g_att'] = 'H'
        else:
            member['g_att'] = 'H'

        att_dict[member_id] = member

    return {'timestamp': absence_taken, 'members': att_dict}


def g_att_lesson(member_nopin, sch_div, absent_id, absence_taken):
    if not absence_taken:
        return 'H'
    sql = "SELECT absen_nilai FROM siswa_absendetail%s \
            WHERE absen_siswa_nopin = '%s' \
                AND absen_id = '%s'" % (sch_div, member_nopin, absent_id)
    g_att = flask_single_item(sql, 'absen_nilai', '')

    if g_att:
        return g_att
    else:
        return '-'


def _excur_att(sch_yr, date, sch_div, kelas_id):
    sch_div = lesson_data['sch_div']
    kelas_id = lesson_data['kelas_id']

    excur_absence_taken = time_excur_g_att_taken(sch_div, sch_yr, date, kelas_id)
    # get a list of members for the group_id
    sql = "SELECT s.siswa_nopin, s.siswa_nama_lengkap \
             FROM siswa_ekskulraport%s er JOIN siswa_%s s \
               ON s.siswa_nopin = er.raport_siswa_nopin \
            WHERE er.raport_tahun_ajaran = '%s' \
              AND raport_ekskul_id ='%s' \
            ORDER BY s.siswa_nama_lengkap" % (sch_div, sch_div, int(sch_yr), kelas_id)
    members = flask_all_plain(sql)

    att_dict = {}
    for member in members:
        siswa_nopin = member['siswa_nopin']

        f_att = f_att_formclass(sch_div, siswa_nopin, date, sch_yr)
        g_att = g_att_excur(sch_div, sch_yr,  date, kelas_id, siswa_nopin, excur_absence_taken)

        member['g_att'] = g_att

        member['f_att'] = f_att
        member['sch_div'] = sch_div
        member['group_type'] = 'excur'

        att_dict[siswa_nopin] = member

    return {'timestamp': excur_absence_taken, 'members': att_dict}


def _moving_att(sch_yr, date, sch_div, group_id, subject_id):
    # sch_div = lesson_data['sch_div']
    # group_id = lesson_data['kelas_id']
    # subject_id = lesson_data['pelajaran_id']
    # user_id = lesson_data['instructor_id']

    absent_id = "%s%s%s%s" % (date, subject_id, group_id, user_id.lower())
    # print ('absent_id:',absent_id)
    lesson_absence_taken = time_lesson_g_att_taken(sch_div, absent_id)

    sql = "SELECT s.siswa_nopin, s.siswa_nama_lengkap, kmc.klapper_keterangan \
             FROM siswa_klappermovingclass%s kmc JOIN siswa_%s s \
               ON s.siswa_nopin = kmc.klapper_siswa_nopin \
            WHERE kmc.klapper_kelas_id='%s' \
            ORDER BY s.siswa_nama_lengkap" % (sch_div, sch_div, group_id)
    members = flask_all_plain(sql)


    att_dict = {}
    for member in members:
        siswa_nopin = member['siswa_nopin']

        f_att = f_att_formclass(sch_div, siswa_nopin, date, sch_yr)
        g_att = g_att_movingclass(sch_div, absent_id, siswa_nopin, lesson_absence_taken)

        if lesson_absence_taken and not g_att:
            g_att = 'H'
        member['g_att'] = g_att
        member['f_att'] = f_att
        member['sch_div'] = sch_div
        member['group_type'] = 'moving'

        att_dict[siswa_nopin] = member

    return {'timestamp': lesson_absence_taken, 'members': att_dict}


def f_att_formclass(sch_div, siswa_nopin, date, sch_yr):
    sql = "SELECT sa.absen_status as f_att \
             FROM siswa_klapper%s sk JOIN siswa_absen%s sa \
               ON sk.klapper_siswa_nopin = sa.absen_siswa_nopin \
            WHERE sk.klapper_siswa_nopin = '%s' \
              AND absen_tanggal = '%s'" % (sch_div, sch_div, siswa_nopin, date)
    f_att = flask_single_item(sql, 'f_att', '-')
    if not f_att:
        f_att = '-'

    return f_att


def g_att_movingclass(sch_div, absent_id, siswa_nopin, lesson_absence_taken):
    if not lesson_absence_taken:
        return 'H'
    sql = "SELECT absen_nilai FROM siswa_absendetail%s \
            WHERE absen_id = '%s' \
              AND absen_siswa_nopin = '%s'" % (sch_div,
                                               absent_id,
                                               siswa_nopin)
    g_att = flask_single_item(sql, 'absen_nilai', '')

    if g_att:
        return g_att
    else:
        return '-'
