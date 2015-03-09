from flask import Flask
import flask
from flask.ext.pymongo import PyMongo
from flask import request
from flask import render_template
import config
from bson import json_util
import datetime
import json

app = Flask(__name__)
app.config['MONGO_URI'] = config.MONGO_URI
mongo = PyMongo(app)

@app.route('/')
def index():
    client_token = request.args.get('token', None)

    if not client_token:
        template_data = {
            "all_tokens" : [t for t in mongo.db.orderresponses.find().distinct("request.client_token") if t] #faster than checking for existance in query
        }
        return render_template('no-token.html', **template_data)

    res = mongo.db.orderresponses.aggregate([
        {"$match" : {"request.client_token": client_token}},
        {"$group" : {
            "_id"               : {"month" : {"$month" : "$_created_at"}, "year" : {"$year" : "$_created_at"}},
            "total_orders"      : {"$sum": 1},
            "gross_earnings"    : {"$sum": "$request.max_price"},
            "amazon_total"      : {"$sum": "$price_components.total"},
            }
        },
        {"$sort": {
            "_id.year" : 1,
            "_id.month" : 1,
            }
        },
        {"$project" : {
            "month" : "$_id.month",
            "year" : "$_id.year",
            "total_orders"      : 1,
            "gross_earnings"    : 1,
            "amazon_total"   : 1,
            "profit": {"$subtract": ["$gross_earnings", "$amazon_total"]}
            }
        }
    ])['result']
   
    template_data = {
        "client_token" : client_token,
        'months' : res
    }

    return render_template('dash.html', **template_data)


@app.route('/monthly')
def monthly_data():
    """
    return metrics for every month to graph 
    """
    client_token = request.args.get('token', None)
    res = mongo.db.orderresponses.aggregate([
        {"$match" : {"request.client_token": client_token}},
        {"$group" : {
            "_id"               : {
                "month" : {"$month" : "$_created_at"},
                "year" : {"$year" : "$_created_at"}
            },
            "total_orders"      : {"$sum": 1},
            "gross_earnings"    : {"$sum": "$request.max_price"},
            "amazon_total"      : {"$sum": "$price_components.total"},
        }},
        {"$project" : {
            "_id" : False,
            "month" : "$_id.month",
            "year" : "$_id.year",
            "total_orders"      : 1,
            "gross_earnings"    : 1,
            "amazon_total"   : 1,
            "profit": {"$subtract": ["$gross_earnings", "$amazon_total"]}
            }
        }
    ])['result']

    metrics = {"total_orders":0, "gross_earnings":0, "profit":0, 'amazon_total':0}
    for r in res:
        for m in metrics.keys():
            metrics[m] += r[m]

    return flask.jsonify(data=res, metrics=metrics)


@app.route('/daily')
def daily_data():
    """
    return metrics for every day in a given month to graph
    """
    client_token = request.args.get('token', None)
    month = int(request.args.get('month', None))
    year = int(request.args.get('year', None))

    #handle date wrap around
    end_month = month+1
    end_year = year
    if end_month > 12:
        end_year +=1
        end_month = 1

    res = mongo.db.orderresponses.aggregate([
        {"$match" : {
            "request.client_token": client_token,
            "_created_at" : {
                    "$gte" : datetime.datetime(year,month,1),
                    "$lt" : datetime.datetime(end_year,end_month,1),
                }
            }
        },
        {"$group" : {
            "_id"               : {
                "month" : {"$month" : "$_created_at"},
                "year" : {"$year" : "$_created_at"},
                "dayOfMonth" : {"$dayOfMonth" : "$_created_at"}
            },
            "total_orders"      : {"$sum": 1},
            "gross_earnings"    : {"$sum": "$request.max_price"},
            "amazon_total"      : {"$sum": "$price_components.total"},
        }}, 
        {"$project" : {
            "_id" : False,
            "day"  : "$_id.dayOfMonth",
            "month" : "$_id.month",
            "year" : "$_id.year",
            "total_orders"      : 1,
            "gross_earnings"    : 1,
            "amazon_total"   : 1,
            "profit": {"$subtract": ["$gross_earnings", "$amazon_total"]}
            }
        }
    ])['result']

    metrics = {"total_orders":0, "gross_earnings":0, "profit":0, 'amazon_total':0}
    for r in res:
        for m in metrics.keys():
            metrics[m] += r[m]

    return flask.jsonify(data=res, metrics=metrics)





if __name__ == "__main__":
	app.run(debug=False)
