#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
#import httplib
import sys
import os
import psycopg2
import psycopg2.extras
import db_config as config
import math
import tempfile

def deg2grad_min_sec(deg):
	# Получаем целую часть:
	#grad=math.fabs(deg)
	# все способы сокращают до целого, в большую сторону, а на нам нужно именно точно:
	grad=int(("%f" % deg).split(".")[0])
	ost=deg-grad
	minutes=int(("%f" % (ost*60)).split(".")[0])
	ost=ost*60-minutes
	sec=ost*60
	return """%d°%d'%.2f" """ % (grad,minutes,sec)


def get_node_info(node_id):
	try:
		# Берём список идентификаторов точек, которым присвоены теги подстанций:
		if config.debug==True:
			print("""select latitude,longitude from nodes where cast(node_id as text) || '-' || cast(version as text) in ( select cast(node_id as text) || '-' || cast(max(version) as text) as tt from nodes group by node_id) and node_id=%(node_id)d limit 1""" % {"node_id":node_id} )
		cur.execute("""select latitude,longitude from nodes where cast(node_id as text) || '-' || cast(version as text) in ( select cast(node_id as text) || '-' || cast(max(version) as text) as tt from nodes group by node_id) and node_id=%(node_id)d limit 1""" % {"node_id":node_id} )
		data = cur.fetchone()
	except:
		print ("I am unable fetch data from db");sys.exit(1)
	node={}
	node["lat"]=((float) (data[0]) )/10000000
	node["lon"]=((float) (data[1]) )/10000000
	# Вычисляем градусы, минуты, секунды:
	node["lat_grad_min_sec"]=deg2grad_min_sec(node["lat"])
	node["lon_grad_min_sec"]=deg2grad_min_sec(node["lon"])

	node["id"]=node_id
	node["map_url"]="http://map.prim.drsk.ru/#map=17/%(lat)f/%(lon)f&layer=Mp&poi=Ka1" % {"lat":node["lat"], "lon":node["lon"]}
	return node

def get_tp_as_nodes(power_tp):
	try:
		# Берём список идентификаторов точек, которым присвоены теги подстанций:
		if config.debug==True:
			print("""select node_id,v from node_tags where cast(node_id as text) || '-' || cast(version as text) in ( select cast(node_id as text) || '-' || cast(max(version) as text) as tt from nodes group by node_id) and node_id in (select node_id from node_tags where (k='power' and v='sub_station')) and k='ref'""" )
		cur.execute("""select node_id,v from node_tags where cast(node_id as text) || '-' || cast(version as text) in ( select cast(node_id as text) || '-' || cast(max(version) as text) as tt from nodes group by node_id) and node_id in (select node_id from node_tags where (k='power' and v='sub_station')) and k='ref'""" )
		# Загоняем значения в set(), преобразуя из списка, т.к. в set() будут только уникальные значения:
		nodes = cur.fetchall()
	except:
		print ("I am unable fetch data from db");sys.exit(1)
	for node in nodes:
		tp={}
		tp["tp_name"]=node[1]
		tp["node"]=get_node_info(node[0])
		# Добавляем данные о линии только если такой линии там нет (она могла быть добавлена как отношение):
		if not tp["tp_name"] in power_tp:
			power_tp[tp["tp_name"]]=tp
	return power_tp


def print_text_power_tp(power_tp):
	print("---------------------------" )
	print("| way_id	|	Имя ТП" )
	print("---------------------------" )
	for tp_name in power_tp:
		tp=power_tp[tp_name]
	#	if len(tp["way_id"]) == 0:
	#		continue
		#print("| %d | %s |" % (tp["way_id"], tp_name) )
		print("'%s'" % (tp_name) )

def print_html_power_tp(lines):
	print("""
		<TABLE BORDER>
		<TR>    
				<TH COLSPAN=5>Текущий список подстанций, полученный из базы данных карты map.prim.drsk.ru</TH>
		</TR>
		<TR>
		<TH>№</TH>
		<TH>Наименование ТП</TH>
		<TH>Ссылка на карту</TH>
		<TH>Десятичные координаты</TH>
		<TH>Координаты в градусах,минутах и секундах</TH>
		</TR>""")
	index=1
	for tp_name in power_tp:
		tp=power_tp[tp_name]

		print("""<TR>
			 <TD>%(index)d</TD>
			 <TD>%(tp_name)s</TD>
			 <TD><a target="_self" href="%(map_url)s">карта</a></TD>
			 <TD>%(lat).6f, %(lon).6f</TD>
			 <TD>%(lat_grad_min_sec)s, %(lon_grad_min_sec)s</TD>
			 </TR>""" % \
			 {"index":index, \
			 "map_url":tp["node"]["map_url"], \
			 "lat":tp["node"]["lat"], \
			 "lon":tp["node"]["lon"], \
			 "lat_grad_min_sec":tp["node"]["lat_grad_min_sec"], \
			 "lon_grad_min_sec":tp["node"]["lon_grad_min_sec"], \
			 "tp_name":tp_name} )
		index+=1

	print("</TABLE>")



# ======================================= main() ===========================

# параметры, переданные скрипту через url:
# http://angel07.webservis.ru/perl/env.html
#param=os.getenv("QUERY_STRING_UNESCAPED")
param=os.getenv("QUERY_STRING")
#param=os.getenv("HTTP_USER_AGENT")
node_id_to_find=0

# Убираем 'n':
#if config.debug:
	#node_id_to_find=19
#	node_id_to_find=16036
#else:
#	node_id_to_find=int(param.strip("n"))


#print "Content-Type: text/html\n\n"; 
if not config.debug:
	print"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<HTML>
<HEAD>
<META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=utf-8">
<TITLE>Список ТП</TITLE>
<META NAME="GENERATOR" CONTENT="OpenOffice.org 3.1  (Linux)">
<META NAME="AUTHOR" CONTENT="Сергей Семёнов">
<META NAME="CREATED" CONTENT="20100319;10431100">
<META NAME="CHANGEDBY" CONTENT="Сергей Семёнов">
<META NAME="CHANGED" CONTENT="20100319;10441400">
<STYLE TYPE="text/css">
<!--
@page { size: 21cm 29.7cm; margin: 2cm }
P { margin-bottom: 0.21cm }
-->
</STYLE>

<style>
   .normaltext {
   }
</style>
<style>
   .ele_null {
    color: red; /* Красный цвет выделения */
   }
</style>
<style>
   .selected_node {
    color: green; /* Зелёный цвет выделения */
	background: #D9FFAD;
	font-size: 150%;
   }
</style>

</HEAD>
<BODY LANG="ru-RU" LINK="#000080" VLINK="#800000" DIR="LTR">
"""
#print("parameters: %s, node_id_to_find=%s" % (param, node_id_to_find) )


try:
	if config.debug:
		print("connect to: dbname='" + config.db_name + "' user='" +config.db_user + "' host='" + config.db_host + "' password='" + config.db_passwd + "'")
	conn = psycopg2.connect("dbname='" + config.db_name + "' user='" +config.db_user + "' host='" + config.db_host + "' password='" + config.db_passwd + "'")
	cur = conn.cursor()
except:
    print ("I am unable to connect to the database");sys.exit(1)

power_tp={}

# Берём все ТП:

get_tp_as_nodes(power_tp)

# Печатаем список ТП:
if config.debug:
	print_text_power_tp(power_tp)
else:
	print_html_power_tp(power_tp)	
sys.exit(0)
