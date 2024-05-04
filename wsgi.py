from app import app

# When running under Gunircorn this is our entry. We have already specified the port to bind
# so just run the app
if __name__ == "__main__":
    app.run(threaded=True, debug=False, use_reloader=False)