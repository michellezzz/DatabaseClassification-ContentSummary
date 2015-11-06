import urllib2
import base64
import sys
import json
import os
import time
from collections import defaultdict


cache = defaultdict(int)
document_samples = defaultdict(int)  # with key using (category, database)
accountKey = ''


class Category(object):
    def __init__(self, label, rules):
        self.children = []
        self.label = label
        self.rules = rules

    def generate_tree(self, root_file):
        file = open(root_file)
        namelist = defaultdict(int)
        for eachline in file:
            item = eachline.strip().split()
            query = '%20'.join(item[1:len(item)])
            if item[0] not in namelist:
                namelist[item[0]] = []
            namelist[item[0]].append(query)
        for node in namelist:
            file_name = node +'.txt'
            child = Category(node, namelist[node])
            try:
                child.generate_tree(file_name)
            except Exception, e:
                child.children = []
            self.children.append(child)


def classify(category, database, t_ec, t_es, especificity_C):
    result = []
    path = category.label

    # If c is a leaf node
    if len(category.children) is 0:
        return [category.label], path

    # Prob database for subcategories
    fq_vec = []
    for child in category.children:
        (fq, urls) = prob_db(child.rules, database)
        fq_vec.append(fq)
        add_urls(category.label, database, urls)

    # Calculate ecoverage, use hash map to represent it
    ecoverage = defaultdict(int)
    for i in range(0, len(fq_vec)):
        ecoverage[category.children[i].label] = calc_cover(fq_vec[i])

    # Calculate especificity, use hash map to represent it
    especificity = defaultdict(int)
    for child in category.children:
        especificity[child.label] = calc_spec(child, ecoverage, especificity_C, category)

    # Print
    for child in category.children:
        print "Specifity for category: ", child.label, "is", especificity[child.label]
        print "Coverage for category: ", child.label, "is", ecoverage[child.label]

    # Get category path recursively, add sample urls recursively
    for child in category.children:
        if especificity[child.label] >= t_es and ecoverage[child.label] >= t_ec:
            tmp_result = classify(child, database, t_ec, t_es, especificity[child.label])
            result.extend(tmp_result[0])
            path = path + '/' + tmp_result[1]
            add_urls(category.label, database, document_samples[(child.label, database)])
    if not result:
        return [category.label], path
    else:
        return result, path


def prob_db(queries, database):
    result = []
    url_retr = []
    for query in queries:
        query = '%20'.join(query.split())
        bingUrl = 'https://api.datamarket.azure.com/Data.ashx/Bing/SearchWeb/v1/Composite?Query=%27site%3a' + database + '%20' + query + '%27&$top=4&$format=json'
        if bingUrl in cache:
            return cache[bingUrl]
        else:
            accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
            headers = {'Authorization': 'Basic ' + accountKeyEnc}
            req = urllib2.Request(bingUrl, headers=headers)
            response = urllib2.urlopen(req)
            content = response.read()
            decoded_json = json.loads(content)
            num = int(decoded_json['d']['results'][0]['WebTotal'])
            result.append(num)
            web_retr = decoded_json['d']['results'][0]['Web']
            for web in web_retr:
                url_retr.append(web['Url'])

    if bingUrl not in cache:
        cache[bingUrl] = (result, url_retr)
    return result, url_retr


def calc_cover(fq):
    sum = 0
    for nq in fq:
        sum += nq
    return sum


def calc_spec(category, ecoverage, especificity_parent, parent):
    sum = 0
    for child in parent.children:
        sum += ecoverage[child.label]
    result = especificity_parent * ecoverage[category.label]
    result = result / float(sum)
    return result


def add_urls(label, database, urls):
    if not urls:
        return
    if (label, database) not in document_samples:
        document_samples[(label, database)] = []
    for url in urls:
        if url not in document_samples[(label, database)]:
            document_samples[(label, database)].append(url)


def print_tree(root):
    print root.label
    print root.rules
    for child in root.children:
        print_tree(child)


def runLynx(url):
    # Ignore all pdf and ppt files
    if str(''.join(url[len(url)-4:len(url)])) == '.pdf':
        return []
    if str(''.join(url[len(url)-4:len(url)])) == '.ppt':
        return []
    if str(''.join(url[len(url)-4:len(url)])) == 'pptx':
        return []

    try:
        buffer = os.popen('lynx --dump ' + url)
    except Exception, e:
        print e
        return []

    recording = True
    wrotespace = False
    output = []
    for cbuf in buffer:
        # Ignore all parts behind reference
        if cbuf.strip():
            if cbuf.split()[0] == "References":
                break
            # Remove all things inside []
            bufftmp = cbuf.strip()
            for charAt in bufftmp:
                if recording:
                    if charAt is '[':
                        recording = False
                        if not wrotespace:
                            output.append(' ')
                            wrotespace = True
                        continue
                    else:
                        if charAt.isalpha():
                            output.append(charAt.lower())
                            wrotespace = False
                        else:
                            if not wrotespace:
                                output.append(' ')
                                wrotespace = True
                else:
                    if charAt is ']':
                        recording = True
                        continue
            output.append(' ')
    output = ''.join(output)
    st = output.split()
    document = []
    for tok in st:
        if tok not in document:
            document.append(tok)
    return document


if __name__ == "__main__":

    # Check input format
    if len(sys.argv) != 5:
        print("Try again. Format: python bing.py <BING_ACCOUNT_KEY> <t_es> <t_ec> <host>")
        sys.exit()
    try:
        accountKey = sys.argv[1]
        t_es = float(sys.argv[2])
        t_ec = int(sys.argv[3])

        if not (0 < t_es < 1):
            print "Try again, t_es should be in range (0, 1)"
            sys.exit()
        if not (t_ec > 0):
            print "Try again, t_ec should > 0"
            sys.exit()
        database = sys.argv[4]

    except Exception, e:
        print "Try again. Format: python bing.py precision query"
        sys.exit()

    # Classification
    root = Category("Root", [])
    root.generate_tree("Root.txt")  # build classification structure

    # Classify
    print "\n\nClassifying..."
    (result, path) = classify(root, database, t_ec, t_es, 1)
    print "\n\nClassification result:"
    print path

    # Content summary
    print "\n\nExtracting topic content summaries..."
    pnodes = path.strip().split('/')
    for pn in pnodes:  # for each category on the path
        if not document_samples[(pn, database)]:
            break
        print "\nCreate topic content summary for:", pn
        summary = open(pn+'-'+database+'.txt', 'w')
        urls = document_samples[(pn, database)]  # get url for this category
        print "Amount of Samples:", len(urls)
        worddict = defaultdict(int)
        for url in urls:
            print "\nGetting page:", url, "\n"
            doctmp = runLynx(url)
            if not doctmp:
                continue
            for word in doctmp:  # count frequency in the document sample
                worddict[word] += 1
            time.sleep(1)

        # sort words in dictionary order
        allwords = []
        for word in worddict:
            allwords.append(word)
        allwords.sort()
        for word in allwords:
            summary.write(word + '#' + str(worddict[word]) + '\n')
        summary.close()

    print "Done"