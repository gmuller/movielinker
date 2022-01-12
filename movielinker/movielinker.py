#!/usr/bin/env python

import tmdbsimple as tmdb
import csv
import os
import configparser
from argparse import ArgumentParser

def main():
    parser = ArgumentParser()
    parser.add_argument("-i", "--movie-id", dest="movie_id", help="Movie ID to link to")
    parser.add_argument(
        "-m", "--movie-name", dest="movie_name", help="Movie name to link to"
    )
    args = parser.parse_args()

    username = os.getenv('MOVIELINKER_USER')
    password = os.getenv('MOVIELINKER_PASSWORD')
    api_key = os.getenv('MOVIELINKER_API')
    
    if username is None: 
      home = os.path.expanduser("~")
      config = configparser.ConfigParser()
      config_file = os.path.join(home, ".movielinker")

      if not os.path.isfile(config_file):
          print("No configuration file found, creating")
          username = input("What is your TMDB Username? ")
          password = input("What is your TMDB Password? ")
          api_key = input("What is your TMDB API Key? ")
          config["movielinker"] = {
              "username": username,
              "password": password,
              "api_key": api_key,
          }
          with open(config_file, "w") as configfile:
              config.write(configfile)

      config.read(os.path.join(config_file))
      username = config["movielinker"]["username"]
      password = config["movielinker"]["password"]
      api_key = config["movielinker"]["api_key"]

    tmdb.API_KEY = api_key

    auth = tmdb.Authentication()
    response = auth.token_new()

    kwargs = {
        "request_token": auth.request_token,
        "username": username,
        "password": password,
    }
    auth = tmdb.Authentication()
    response = auth.token_validate_with_login(**kwargs)

    kwargs = {"request_token": auth.request_token}
    auth = tmdb.Authentication()
    response = auth.session_new(**kwargs)
    session_id = response["session_id"]

    account = tmdb.Account(session_id)
    response = account.info()
    response = account.lists()

    print("\nWhich list contains the movies you have already seen?\n")
    index = 0
    movie_lists = []
    for l in response["results"]:
        print(index, l["name"])
        movie_lists.append({"id": l["id"], "name": l["name"]})
        index += 1
    list_index = int(input())
    list_id = movie_lists[list_index]["id"]
    a = tmdb.Lists(list_id)

    movie_id = args.movie_id

    if args.movie_name != None:
        search = tmdb.Search()
        response = search.movie(query=args.movie_name)
        index = 0
        foundMovies = []
        for s in search.results:
            foundMovies.append({"id": s["id"], "title": s["title"]})
            print(index, s["title"], s["release_date"])
            index += 1
        movie_index = int(input("\nWhich Movie ID did you mean?\n"))
        movie_id = foundMovies[movie_index]["id"]
        print("\nGetting cast list for", foundMovies[movie_index]["title"], "\n")

    movie = tmdb.Movies(movie_id)

    collaboratorList = []
    index = 0
    for c in movie.credits()["cast"]:
        collaboratorList.append({"id": c["id"], "name": c["name"]})
        print(index, c["name"])
        index += 1

    excluded_collaborator_index = int(input("\nExclude a cast member?\n"))
    excluded_collaborator = collaboratorList[excluded_collaborator_index]
    print("Excluding", excluded_collaborator["name"])

    response = movie.info()
    list_response = a.info()
    seen = set()
    [seen.add(movie["id"]) for movie in a.items]

    cache = {}
    for c in movie.credits()["cast"]:
        if c["id"] == excluded_collaborator["id"]:
            continue
        person = tmdb.People(c["id"])
        response = person.info
        for p in person.movie_credits()["cast"]:
            if p["vote_count"] < 40:
                continue
            if p["id"] in seen:
                continue
            if p["id"] in cache:
                cache[p["id"]]["collaborators"].add(c["name"])
            else:
                p["collaborators"] = {c["name"]}
                cache[p["id"]] = p

    filename = "".join(x for x in movie.title if x.isalnum()) + ".csv"
    with open(filename, "w") as csv_file:
        fields = [
            "id",
            "title",
            "collaborators",
            "vote_average",
            "vote_count",
            "release_date",
            "overview",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for movie in sorted(
            list(cache.values()), key=lambda x: x["vote_average"], reverse=True
        ):
            writer.writerow(movie)
            # print(str(movie['id']) + ", " + movie['title'] + ", " + str(movie['collaborators']) + ", " + str(movie['vote_average']))

    print("complete")


if __name__ == "__main__":
    main()
