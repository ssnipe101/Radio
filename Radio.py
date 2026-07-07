# TODO Refactor main to smaller functions
# TODO Give LLM rolling memory
# TODO Add a NoAI option on startup

from tkinter import ACTIVE, LAST
from winsound import PlaySound
from mutagen.id3 import ID3NoHeaderError
from cerebras.cloud.sdk import Cerebras
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from flask import Flask, Response, before_render_template
from waitress import serve
import subprocess as SubP
import threading
import edge_tts
import platform
import asyncio
import random
import time
import stat
import uuid
import sys
import os

class Queue():
    def __init__(self) :
        self.list = []

    def add(self, input):
        self.list.append(input)
    
    def get(self) : 
        if len(self.list) > 0 :
            return self.list.pop(0)
        else :
            return ("EMPTY")

class MusicSelection():
    def __init__(self):
        self.activemusic = []
        self.inactivemusic = []
        for root, _, files  in os.walk(MUSICPATH):
            for f in files:
                if f.endswith((".flac", ".mp3")):
                     self.activemusic.append(os.path.join(root, f))
        if not self.activemusic :
            sys.exit(f"NO MUSIC IN {MUSICPATH}")
            time.sleep(5)

        self.activemusic = quickSort(self.activemusic)

    def resetSongList(self) :
        for i in range(self.inactivemusic) :
            self.activelist.append(self.inactivemusic[i])
            self.inactivelist.pop[i]

    def getSong(self):
        if not len(self.activemusic) == 0 :
            selection = random.choice(self.activemusic)
            pos = binarySearch(self.activemusic, selection)

            self.activemusic.pop(pos)

            self.inactivemusic.append(selection)

            return selection
        else :
            self.resetSongList()

def quickSort(L) :
    leftList = []
    middleList = []
    rightList = []

    if len(L) <= 1 :
        return(L)

    pivot = L[len(L)//2]

    for key in L :
        if key > pivot :
            rightList.append(key)
        elif key < pivot :
            leftList.append(key)
        elif key == pivot :
            middleList.append(key)

    return(quickSort(leftList) + middleList + quickSort(rightList))

def binarySearch(L, key) :
    left = 0
    right = (len(L)-1)

    while left <= right:
        mid = (right + left)//2

        if key < L[mid] :
            right = mid
        elif key > L[mid] :
            left = mid
        elif key == L[mid] :
            return mid

    raise ValueError
 
def LLM(firstSong, lastSong):
    try :    
       with open(APIPATH, "r") as f :
           API = f.read().strip()

       if not API :
           raise ValueError
    except (FileNotFoundError, ValueError):
       API = input("Input API key ").strip()

    with open(APIPATH, "w") as f :
        f.write(API)

    client = Cerebras(
        api_key = API
    )
    try :
        chat_completion = client.chat.completions.create(
            messages=[
                {
    
                
                    "role": "system",
                    "content": f"You are a Female radio presenter called Emily, The previous 2 songs played were {firstSong} and {lastSong}(this has already been played) in that order, do not describe your actions only your words, do not make up what is coming up next you dont know. Title, album or artist will say Unknow Artist/Title/Album if its unknow, anmything else and that is the name of the title/artist/album"
                 
                }
        ],
            model="gpt-oss-120b",
        )
        return(chat_completion.choices[0].message.content)
    
     
    except Exception as e:

        try:
            error_code = e.response.status_code
            if error_code == 401:
                
                print("ERROR 401 INVALID API KEY")
        
                API = input("Input API key").strip()
        
                with open(APIPATH, "w") as f :
                        f.write(API)
                
                return(LLM())
            elif error_code == 429:
                return("Cereberus is facing high traffic right now please try again later")
        
            elif error_code == 404 :
                 return("ERROR CEREBERUS MODEL NOT FOUND")
        
            elif error_code != 200:
                print(f"CEREBERUS ERROR CODE : {error_code}")
                return("AN UNKNOWN ERROR OCCURED")
        except :
            print(f"Error Code Type : {type(e)}")
            print(f"Error Details : {e}")
            return("AN ERROR OCCURED")

async def ttsAudioGeneration(text):

    communication = edge_tts.Communicate(text, "en-IE-EmilyNeural", rate="+15%")

    await communication.save(SPEECHPATH)

def streamOutput(LOCATION, Metadata) :

    song_title = Metadata.get("title", ["Unknown"])[0]
    song_artist = Metadata.get("artist", ["Unknown"])[0]

    process = SubP.Popen([
        FFMPEGPATH,
        "-re",
        "-i", LOCATION,
        "-map", "0:a:0",        
        "-ar", "44100",        
        "-ac", "2",            
        "-c:a", "mp3",
        "-q:a", "2",
        "-metadata", f"title={song_title}",
        "-metadata", f"album={song_artist}",
        "-f", "mp3",         
        "pipe:1"
    ], stdout=SubP.PIPE, stderr=SubP.DEVNULL)

    try:
        while process.poll() is None:
            chunk = process.stdout.read(4096)
        
            if chunk:
                yield chunk
    finally :
        process.kill()
        process.wait()

def main() :
    
    activeMusicList = MusicSelection()    
    while True:      


        selectedSong1, selectedSong2 = activeMusicList.getSong(), activeMusicList.getSong()

        while selectedSong2 == selectedSong1 :
            selectedSong2 = random.choice(activeMusicList)

        if selectedSong1.endswith(".mp3"):
            path = os.path.join(MUSICPATH, selectedSong1)
            try :
                songPlayed = EasyID3(path)
            except ID3NoHeaderError :
                EasyID3().save(path)
                songPlayed = EasyID3(path)
                if not songPlayed.get("title") :
                    songPlayed["title"] =  "Unknown Title"
                if not songPlayed.get("album") :
                    songPlayed["album"] =  "Unknown Album"
                if not songPlayed.get("artist") :
                    songPlayed["artist"] =  "Unknown Artist"

                songPlayed.save(path)
        elif selectedSong1.endswith(".flac"):
            path = os.path.join(MUSICPATH, selectedSong1)

            songPlayed = FLAC(path)
            if not songPlayed.get("title") :
                songPlayed["title"] =  "Unknown Title"
            if not songPlayed.get("album") :
                songPlayed["album"] =  "Unknown Album"
            if not songPlayed.get("artist") :
                songPlayed["artist"] =  "Unknown Artist"

            songPlayed.save(path)

        if selectedSong2.endswith(".mp3"):
            path = os.path.join(MUSICPATH, selectedSong2)
            try :
                songPlayed2 = EasyID3(path)
            except ID3NoHeaderError :
                EasyID3().save(path)
                songPlayed2 = EasyID3(path)
                if not songPlayed2.get("title") :
                    songPlayed2["title"] =  "Unknown Title"
                if not songPlayed2.get("album") :
                    songPlayed2["album"] =  "Unknown Album"
                if not songPlayed2.get("artist") :
                    songPlayed2["artist"] =  "Unknown Artist"

                songPlayed2.save(path)
        elif selectedSong2.endswith(".flac") :
            path = os.path.join(MUSICPATH, selectedSong2)

            songPlayed2 = FLAC(path)
            if not songPlayed2.get("title") :
                songPlayed2["title"] =  "Unknown Title"
            if not songPlayed2.get("album") :
                songPlayed2["album"] =  "Unknown Album"
            if not songPlayed2.get("artist") :
                songPlayed2["artist"] =  "Unknown Artist"

            songPlayed2.save(path)



        speechPlayed = {
                        "artist": "Emily",
                        "album": "Edge_tts",
                        "title": "Speech Broadcast"
                        }                    

        SONGPATH = os.path.join(MUSICPATH, selectedSong1)
        SONGPATH2 = os.path.join(MUSICPATH, selectedSong2)

        print(f"Now Playing : {songPlayed.get("title",["Unknown"])[0]}")
        print(f"Up Next : {songPlayed2.get("title",["Unknown"])[0]}")


        script = (LLM(songPlayed, songPlayed2))
        
        threading.Thread(target=lambda: asyncio.run(ttsAudioGeneration(script)),daemon=True).start()

        newCycle = True
        i = 0
        while i <= 1:
            if newCycle :
                yield from streamOutput(SONGPATH, songPlayed)
                newCycle = False
                i += 1
            elif not newCycle :
                yield from streamOutput(SONGPATH2,songPlayed2)
                newCycle = True
                i += 1
        
        yield from streamOutput(SPEECHPATH, speechPlayed)

def broadCaster() :
    while True:
        print("Broadcast Active")
        for chunk in main():  
            try :
                for userID in activelistener :
                    dict[userID].add(chunk)
            except Exception as e:
                print(f"ERROR TYPE IS {type(e).__name__} LINE 309(probably)")
                print(f"ERROR message IS {e} LINE 309(probably)")

                time.sleep(5)

def listener(userID):
    try :
        while True:
            playChunk = dict[userID].get()
            if playChunk == "EMPTY":
                time.sleep(0.1)
                pass
            else :
                yield playChunk
    except GeneratorExit :
        activelistener.remove(userID)

#driver code

if getattr(sys, 'frozen', False):
    IBASEPATH = sys._MEIPASS
    EBASEPATH = os.path.dirname(sys.executable)
else :
    IBASEPATH = os.path.dirname(__file__)
    EBASEPATH = os.path.join(os.path.dirname(__file__), "..")

EDITPATH = os.path.join(EBASEPATH, "RadioData")


os.makedirs(EDITPATH, exist_ok=True)

MUSICPATH = os.path.join(EDITPATH, "Music")
SPEECHPATH = os.path.join(IBASEPATH, "Audio", "Speech", "Speech.mp3")
DATAPATH = os.path.join(IBASEPATH, "Data")
APIPATH = os.path.join(EDITPATH, "API.txt")
PORTPATH = os.path.join(EDITPATH, "Port")
SCRIPTLOCATION = os.path.join(IBASEPATH, "Audio", "Speech", "scripts", "Script.txt")

os.makedirs(MUSICPATH, exist_ok=True)
os.makedirs(PORTPATH,  exist_ok=True)


if platform.system() == "Windows":
    FFMPEGPATH = os.path.join(IBASEPATH, "bin", "FFmpeg", "Windows", "ffmpeg-7.1.1", "bin", "ffmpeg.exe")
else :
    FFMPEGPATH = os.path.join(IBASEPATH, "bin", "FFmpeg", "Linux", "ffmpeg-git-20240629-amd64-static", "ffmpeg")

    try:
        os.chmod(FFMPEGPATH,os.stat(FFMPEGPATH).st_mode | stat.S_IEXEC)
    except Exception:
        raise RuntimeError(f"FFMPEG IS NOT EXECUTABLE PLEASE RUN : chmod +x {FFMPEGPATH}")

if(MUSICPATH) :
    try :
        with open(os.path.join(PORTPATH, "Port.txt"), "r") as f :
            PORT = f.read().strip()
        
    except FileNotFoundError:
        with open(os.path.join(PORTPATH, "Port.txt"), "w") as f :
            f.write(input("PORT MISSING, INPUT PORT NOW : "))

        with open(os.path.join(PORTPATH, "Port.txt"), "r") as f :
            PORT = f.read().strip()

else :
    os.mkdir(MUSICPATH)

    try :
        with open(os.path.join(PORTPATH, "Port.txt"), "r") as f :
            PORT = f.read().strip()
        
    except FileNotFoundError:
        with open(os.path.join(PORTPATH, "Port.txt"), "w") as f :
            f.write(input("PORT MISSING, INPUT PORT NOW : "))

        with open(os.path.join(PORTPATH, "Port.txt"), "r") as f :
            PORT = f.read().strip()

dict = {}
activelistener = []

threading.Thread(target=broadCaster, args=(), daemon=True).start()

app = Flask(__name__)
@app.route("/stream")


def stream() :

    userID = uuid.uuid4()
    
    global dict, activelistener

    dict[userID] = Queue()
    activelistener.append(userID)

    print(activelistener)
    
    time.sleep(1)

    return Response(listener(userID), mimetype="audio/mpeg")

try :
    if __name__ == "__main__":
        serve(app, host="0.0.0.0", port=PORT)
except Exception as e :
    pass