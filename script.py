from http.server import HTTPServer, BaseHTTPRequestHandler
import io
import json

class DataControl:
    """ Control cytes list; argument file, fiekeys - str, path from work directory, to data file and file with keys respectively """

    def __init__(self, file, filekeys):
        print("\nLoading data. Please wait...\n")
        f = io.open(filekeys, encoding='utf-8')
        self.keys = f.read()
        self.keys = self.keys.translate({ord(s) : None for s in "' "})
        self.keys = self.keys.split(',')
        f.close()
        self.data = list()
        f = io.open(file, encoding='utf-8')
        for line in f:
            current = line.split('\t')
            current[-1] = current[-1].replace('\n', '')
            self.data.append(dict((map(lambda *args: args, self.keys, current))))
            self.data[-1]["alternatenames"] = self.data[-1]["alternatenames"].split(',')
        f.close()
    
    def find_id(self, geo_id):
        for element in self.data:
            if geo_id == element['geonameid']:
                return element
        return None

    def find_name(self, name):
        max_population = 0
        target = None
        for element in self.data:
            element['population'] = int(element['population'])
            if name == element['name'] or name == element['asciiname']:
                if max_population <= element['population']:
                    max_population = element['population']
                    target = element
            for i in element['alternatenames']:
                if name == i:
                    if max_population <= element['population']:
                        max_population = element['population']
                        target = element
        return target
    
    def find_start(self, start):
        prompt = list()
        for element in self.data:
            if element['name'].startswith(start):
                prompt.append(element['name'])
                continue
            if element['asciiname'].startswith(start):
                prompt.append(element['asciiname'])
                continue
            for i in element['alternatenames']:
                if i.startswith(start):
                    prompt.append(i)
                    continue
        return prompt



class RequestHandler(BaseHTTPRequestHandler):
    """ methods for task """

    controller = DataControl('data/RU.txt', 'data/keys.txt')
    print("Server ready to work\n")

    def do_GETID(self):
        geoid = self.path.replace('/', '')
        target = self.controller.find_id(geoid)
        if target is None:
            self.reply(404, {'Error' : 'Not found'})
        else:
            new_keys = list()
            for key in self.controller.keys:
                if target[key] == '':
                    del target[key]
                else:
                    new_keys.append(key)
            self.reply(200, {'Result' : target})
        
    def do_FINDON(self):
        number = self.path.translate({ord(sym) : None for sym in '/'})
        try:
            number = int(number)
        except ValueError:
            return self.reply(400, { 'Error' : 'Bad Request'})
        number_of_bits = int(self.headers['Content-Length'])
        data = self.rfile.read(number_of_bits)
        try:
            data = data.decode('utf-8')
        except Exception:
            try:
                data = data.decode('cp1251')
            except Exception:
                return self.reply(400, { 'Error' : 'Bad Input Page'})
        data = data.translate({ord(sym) : ord(' ') for sym in ".,!?/" })
        data = data.split(' ')
        count = len(data)
        while count >= 0:
            count -= 1
            data[count] = data[count].translate({ord('_') : ord(' ')})
            if data[count] == '':
                del data[count]
        result = dict()
        count = 0
        for word in data:
            target = self.controller.find_name(word)
            if target is not None:
                count += 1
                key = 'Result' + str(count)
                result[key] = target
            if count == number:
                break
        self.reply(200, result)

    def do_DIFF(self):
        number_of_bits = int(self.headers['Content-Length'])
        data = self.rfile.read(number_of_bits)
        try:
            data = data.decode('utf-8')
        except Exception:
            try:
                data = data.decode('cp1251')
            except Exception:
                return self.reply(400, { 'Error' : 'Bad Input Page'})
        data = data.translate({ord('.') : None})
        data = data.split(',')
        if len(data) != 2:
            return self.reply(400, {'Error' : 'Wrong number of arguments, two expected!'})
        if data[1][0] == ' ':
            data[1] = data[1][1:]
        print(data)
        target1 = self.controller.find_name(data[0])
        target2 = self.controller.find_name(data[1])
        if target1 == None or target2 == None:
            return self.reply(400, { 'Error' : 'Not Found'})
        timezones = dict()
        f = io.open('data/time.txt')
        for line in f:
            line = line.split(' ')
            line[0] = line[0].translate({ord("'") : None})
            timezones[line[0]] = int(line[1])
        f.close()
        answer = dict()
        if target1['timezone'] != '' and target2['timezone'] != '':
            answer['Difference of timezones'] = str(abs(timezones[target1['timezone']] - timezones[target2['timezone']])) + ' hours'
        else:
            answer['Difference of timezones'] = 'Unfortunately, impossible to calculate'
        if target1['longitude'] != '' and target2['longitude'] != '':
            longtitudediff = float(target1['longitude']) - float(target2['longitude'])
            if longtitudediff < 0:
                answer['Difference of longitude'] = data[0] + ' farther north than ' + data[1]
            elif longtitudediff == 0:
                answer['Difference of longitude'] = 'Both on one longitude'
            else:
                answer['Difference of longitude'] = data[1] + ' farther north than ' + data[0]
        else:
            answer['Difference of longitude'] = 'Unfortunately, impossible to calculate'
        answer['Information about first'] = target1
        answer['Information about second'] = target2
        self.reply(200, answer)
    
    def do_HELPWRITE(self):
        number_of_bits = int(self.headers['Content-Length'])
        data = self.rfile.read(number_of_bits)
        try:
            data = data.decode('utf-8')
        except Exception:
            try:
                data = data.decode('cp1251')
            except Exception:
                return self.reply(400, { 'Error' : 'Bad request'})
        result = self.controller.find_start(data)
        if len(result) != 0:
            answer = str()
            for i in result:
                answer = answer + i +', '
            self.reply(200, {'You mean:' : answer})
        else:
            self.reply(200, {'Result': 'No matches'})

    def reply(self, code, message):
        """Formats answer as html and writes"""
        if message is not None:
            body = json.dumps(message, sort_keys=False, indent=4, ensure_ascii=False, cls=json.JSONEncoder).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf=8')
            self.send_header('Content-Length',  len(body))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        else:
            self.send_response(204)


if __name__ == '__main__':
    HTTPServer(('', 8000), RequestHandler).serve_forever()