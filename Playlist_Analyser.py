# Spotify Playlist Analyser
# Author: Rucha Chandorkar
# Summer of Code 2023

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from configparser import ConfigParser

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from wordcloud import WordCloud

from math import pi
import sys

# Get the configparser object
config = ConfigParser()
config.read('config.ini')
cid = config['SpotifyApp']['ClientID']
secret = config['SpotifyApp']['ClientSecret']

# Authentication - without user
client_credentials = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials)

# Define list of playlists for comparison along with the genre
PLAYLISTS = [
    ("https://open.spotify.com/playlist/37i9dQZF1EQncLwOalG3K7", "Pop"),
    ("https://open.spotify.com/playlist/37i9dQZF1DWVmps5U8gHNv", "Folk"),
    ("https://open.spotify.com/playlist/37i9dQZF1DWWEJlAGA9gs0", "Classical"),
    ("https://open.spotify.com/playlist/37i9dQZF1DWXRqgorJj26U", "Rock"),
    ("https://open.spotify.com/playlist/37i9dQZF1DX5hHfOi73rY3", "Dance")
]

LABELS = {
    'danceability': "Danceability",
    'energy': "Energy",
    'instrumentalness': "Instrumentalness",
    'speechiness': "Speechiness",
    'valence': "Optimism",
    'popularity': "Popularity"
}

"""Get relevant data from a playlist url"""
def get_playlist_data(url):
    playlist_URI = url.split("/")[-1].split("?")[0]
    playlist_tracks = sp.playlist_tracks(playlist_URI)

    data = {'track_id':[],'artist_name':[],'track_name':[],'danceability':[], 'energy':[], 'instrumentalness':[], 'speechiness':[], 'valence':[], "popularity":[]}
    df = pd.DataFrame(data)

    track_ids = []
    for track in playlist_tracks["items"]:
        track_ids.append(track["track"]["id"])
        # Prepare the new row to be added
        new_row = {
                    'track_id': track["track"]["id"],
                    'artist_name' : track["track"]["artists"][0]["name"],
                    'track_name' : track["track"]["name"],
                    'energy': None, 
                    'danceability': None, 
                    'instrumentalness': None, 
                    'speechiness': None, 
                    'valence': None, 
                    'popularity':track["track"]["popularity"],
                }

        # Add the new data to the DataFrame
        df.loc[len(df)] = new_row

    # Audio Features in batches of 100
    start_idx = 0
    while start_idx < len(track_ids):
        audio_features_list = sp.audio_features(track_ids[start_idx:start_idx+100])

        for audio_features in audio_features_list:
            # update the audio features
            df.loc[df['track_id'] == audio_features['id'], 'danceability'] = audio_features["danceability"]
            df.loc[df['track_id'] == audio_features['id'], 'instrumentalness'] = audio_features["instrumentalness"]
            df.loc[df['track_id'] == audio_features['id'], 'speechiness'] = audio_features["speechiness"]
            df.loc[df['track_id'] == audio_features['id'], 'valence'] = audio_features["valence"]

        start_idx += 100

    return df


"""
Find the occurences of each value in a column in the dataframe and return as a dictionary
e.g. df_to_freq(df, 'artist_name')
"""
def df_to_freq(df, column):
    # Select column values
    df_counts = df.groupby([column]).size().reset_index(name='count')
    df_dict = {}

    for _, row in df_counts.iterrows():
        df_dict[row[column]] = row['count']

    return df_dict


"""Preprocess the playlist dataframe to be converted into a spider graph"""
def preprocess_df(df):
    # remove unneeded columns and then convert data to percentages
    processed = df.drop(["track_id", "artist_name", "track_name"], axis=1).mean(axis=0).copy()
    new_df = pd.DataFrame(processed).transpose()
    new_df.loc[:, new_df.columns != "popularity"] *= 100

    return new_df


"""Convert processed data from a playlist into a spider graph"""
def make_spider_graph(df, gs, current_index, title, colour):
    categories = list(df)
    num_categories = len(categories)

    # get values for the graph
    values = df.loc[0].values.flatten().tolist()
    values += values[:1] # needed to make the circle complete

    # calculate angles for the graph
    angles = [n / float(num_categories) * 2 * pi for n in range(num_categories)]
    angles += angles[:1]

    if current_index < int((len(PLAYLISTS) + 1)/2):
        x = 0
        y = current_index
    else:
        x = 1
        y = current_index - int((len(PLAYLISTS) + 1)/2)

    ax = plt.subplot(gs[x, y], polar=True)

    # Draw one axis per variable + add labels
    plt.xticks(angles[:-1], LABELS.values(), color='grey', size=8)
    
    # Draw ylabels
    ax.set_rlabel_position(0)
    plt.yticks([25,50,75], ["25%","50%","75%"], color="grey", size=7)
    plt.ylim(0,100)

    plt.title(title)
    
    # Plot data
    plt.plot(angles, values, color=colour, linewidth=1, linestyle='solid')
    
    # Fill area
    plt.fill(angles, values, facecolor=colour, alpha=0.5)


def main(playlist_link):
    # generate wordcloud for user playlist
    df = get_playlist_data(playlist_link)
    artist_freq = df_to_freq(df, 'artist_name')
    mywordcloud = WordCloud(max_font_size=50, max_words=100, background_color="white").generate_from_frequencies(artist_freq)
    # mywordcloud.to_file('mywordcloud.png')

    num_playlists = len(PLAYLISTS) + 1
    i = 0
    cm = plt.cm.get_cmap('hsv', num_playlists)

    gs = GridSpec(nrows=3, ncols=int(num_playlists/2))

    make_spider_graph(preprocess_df(df), gs, i, "Your Playlist", cm(i))

    for playlist, genre in PLAYLISTS:
        i += 1
        df = get_playlist_data(playlist)
        make_spider_graph(preprocess_df(df), gs, i, genre, cm(i))

    ax = plt.subplot(gs[2, :])
    ax.imshow(mywordcloud, interpolation="bilinear")
    ax.axis("off")

    # plt.subplots_adjust(wspace=0.75)
    plt.tight_layout(pad=0.5)
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("No playlist specified, please specify playlist url.")
        print("E.g.: https://open.spotify.com/playlist/37i9dQZEVXbNG2KDcFcKOF?si=1333723a6eff4b7f")
        main(input("URL: "))

    else:
        main(sys.argv[1])