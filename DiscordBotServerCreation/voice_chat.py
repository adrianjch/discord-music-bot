from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    id: int = -1
    days: int = -1
    lastDay: int = -1
    seconds: int = -1
    lastConnected: int = -1
    kickedCount: int = -1

class Helper:
    users = {}
    albertKickCounter = 0
    lastAuditLogEntry = -1
    lastAuditLogEntryCounts = -1

    def __init__(self):
        f = open("data/vc_stats.txt", "r")
        for line in f.readlines():
            # Remove whitespace
            line = line.replace('\n', '')
            # Split csv
            group = line.split(',')
            # Add user to list
            user = User()
            user.id = int(group[0])
            user.days = int(group[1])
            user.lastDay = int(group[2])
            user.seconds = int(group[3])
            user.kickedCount = int(group[4])
            self.users[user.id] = user
        f.close()

        f = open("data/albert.txt", "r")
        text = f.read().replace('\n', '')
        group = text.split(',')
        self.albertKickCounter = int(group[0])
        self.lastAuditLogEntry = int(group[1])
        self.lastAuditLogEntryCounts = int(group[2])
        f.close()

    def saveVoiceStats(self):
        # Save on file
        f = open("data/vc_stats.txt", "w")
        for user in self.users.values():
            f.write(f'{user.id},{user.days},{user.lastDay},{user.seconds},{user.kickedCount}\n')
        f.close()

    def saveAlbertStats(self):
        # Save on file
        f = open("data/albert.txt", "w")
        f.write(f'{self.albertKickCounter},{self.lastAuditLogEntry},{self.lastAuditLogEntryCounts}')
        f.close()

    def increaseAlbertKick(self, entry, memberId):
        self.albertKickCounter += 1
        self.lastAuditLogEntry = entry.id
        self.lastAuditLogEntryCounts = entry.extra.count
        self.users[memberId].kickedCount += 1
        self.saveAlbertStats()

    def albertKicked(self, entry):
        return entry.user.id == 278541333449408517 and (entry.id != self.lastAuditLogEntry or entry.extra.count != self.lastAuditLogEntryCounts)

    def memberConnected(self, id):
        dayOfYear = datetime.now().timetuple().tm_yday
        # Update values
        if id in self.users:
            self.users[id].days += 1
            self.users[id].lastDay = dayOfYear
        else:
            user = User()
            user.id = id
            user.days = 1
            user.lastDay = dayOfYear
            user.seconds = 0
            self.users[user.id] = user
        # Save on file
        self.saveVoiceStats()

    def updateMember(self, id):
        now = int(datetime.timestamp(datetime.now()))
        user = self.users[id]
        if user.lastConnected != -1:
            user.seconds += now - user.lastConnected
            self.saveVoiceStats()
        user.lastConnected = now

    def userJustJoined(before, after):
        return before.channel == None and after.channel != None

    def userJustLeft(before, after):
        return before.channel != None and after.channel == None

    def userConnectedToday(self, id):
        if id not in self.users:
            return False
        dayOfYear = datetime.now().timetuple().tm_yday
        return self.users[id].lastDay == dayOfYear
