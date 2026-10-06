from flask import Flask, send_from_directory, jsonify, request
from urllib.request import Request, urlopen
import json

app = Flask(__name__, static_folder=".")


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "online": True,
        "ai": False,
        "fivem": True
    })


@app.route("/api/fivem")
def fivem_servers():

    search = request.args.get("search", "").lower().strip()
    limit = 50

    url = "https://servers-frontend.fivem.net/api/servers/stream/"

    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urlopen(req, timeout=15) as response:
            data = response.read().decode("utf-8")

        servers = []

        # FiveM قد يرجع JSON متتابع
        decoder = json.JSONDecoder()
        position = 0

        while position < len(data):
            data = data.lstrip()
            position = len(data) - len(data.lstrip())

            if position >= len(data):
                break

            try:
                obj, end = decoder.raw_decode(data[position:])
                position += end

                if isinstance(obj, dict):
                    servers.append(obj)

            except json.JSONDecodeError:
                break

        result = []

        for server in servers:

            name = (
                server.get("hostname")
                or server.get("sv_projectName")
                or "FiveM Server"
            )

            players = server.get("players", [])

            if isinstance(players, list):
                player_count = len(players)
            else:
                player_count = server.get("clients", 0)

            max_players = (
                server.get("sv_maxclients")
                or server.get("maxClients")
                or 0
            )

            region = (
                server.get("locale")
                or server.get("country")
                or "Unknown"
            )

            gametype = (
                server.get("gametype")
                or server.get("gameType")
                or "FiveM"
            )

            map_name = (
                server.get("mapname")
                or server.get("mapName")
                or "GTA V"
            )

            searchable = (
                str(name) + " "
                + str(region) + " "
                + str(gametype) + " "
                + str(map_name)
            ).lower()

            if search and search not in searchable:
                continue

            result.append({
                "name": str(name),
                "players": player_count,
                "maxPlayers": int(max_players or 0),
                "region": str(region),
                "gametype": str(gametype),
                "map": str(map_name),
                "online": True
            })

            if len(result) >= limit:
                break

        return jsonify({
            "success": True,
            "count": len(result),
            "servers": result
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "count": 0,
            "servers": [],
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )