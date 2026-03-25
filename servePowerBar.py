from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# default slider value
CURRENT_VALUE = 150

@app.route("/")
def index():
    return render_template("index.html", value=CURRENT_VALUE)

@app.route("/getData")
def get_data():
    global CURRENT_VALUE
    
    value = request.args.get("value", type=int)

    # If no value was passed, return the last known slider value
    if value is not None:
        CURRENT_VALUE = value

    return jsonify({"sliderValue": CURRENT_VALUE})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
