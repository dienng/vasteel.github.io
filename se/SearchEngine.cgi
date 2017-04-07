#!/usr/bin/python2
import cgi
import cgitb; cgitb.enable()
print "Content-type: text/html\n"
print

import re
import numpy as np
import urllib2

# Class SearchEngine
# Allows user to create a decently competent search engine with their own
#   universe of web pages and dictionary of "legal" words
class SearchEngine:
    # initialize the search engine with a universe of urls and a dictionary
    def __init__(self,urls,word_dict):
        self._urls = str(urls)
        self._urls = list(set(self._urls.split()))
        n = len(self._urls)
        self._url_index = {self._urls[i] : i for i in range(n)}
        self._word_dict = word_dict
        self.refresh_cache()

    # "public" function update_dict()
    # for when you want just want a new dictionary
    def update_dict(self,new_dict):
        self._word_dict = new_dict
        return

    # "public" function refresh_cache()
    # allows user to get the new pages in their universe
    # this is convenient when the web pages change
    def refresh_cache(self):

        n = len(self._urls)
        self._cached_pages=[None]*n
        self._clean_cached_pages=[None]*n
        for i in range(n):
            url = self._urls[i]
            try:
                txt = urllib2.urlopen(url).read()
                self._cached_pages[i] = txt
                # _clean_cached_pages need to be easily readable by normal users
                self._clean_cached_pages[i] = self._strip_html(txt)
            except:
                self._cached_pages[i] = ''
                self._clean_cached_pages = ''
        # regenerate network to incorporate changes to web pages
        self._generate_network()
        return

    # "private" function _strip_html()
    # takes a string and removes all html tags, returning a string of mostly words, used for searching
    def _strip_html(self,txt):
        pat = re.compile('<.*?>')
        clean = re.sub(pat, '', txt)
        # replace white space with a space so it's easily readable by humans
        clean = ' '.join(clean.split())
        return clean

    # "private" function _generate_network()
    # assumes list of urls separated by white space
    # from the list of urls, function generates a weighted and directed adjacency matrix
    def _generate_network(self):
        n = len(self._urls)
        self._N = np.zeros((n,n),dtype=int)
        # go through each web page and search for links
        for i in range(n):
            url = self._urls[i]
            # it takes a long time to read pdf files, also can't read them with any clarity, so don't read them
            if url[len(url)-4:] == '.pdf':
                continue
            page = self._cached_pages[i]
            # find href links
            m = re.findall(r'href="(.*?)"', page, re.I)
            if len(m) != 0:
                for found_url in m:
                    # get full url from relative url
                    if found_url[:4] != 'http':
                        found_url = urllib2.urlparse.urljoin(url,found_url)
                        found_url = urllib2.quote(found_url, safe=':/~')


                    # make the connection
                    if found_url in self._url_index.keys():
                        self._N[self._url_index[found_url],i]+=1
        return

    # "public" function query()
    # allows user to search their "internet" with keywords
    # takes a query of type string, returning num_results number of results
    # knows the difference for quotation marks
    # prints search results with all the flairs but actually returns the ranked urls
    def query(self, input_query, num_results):
        quoted, unquoted = self._parse_search_query(input_query)

	# TODO:less awkward way maybe
        #if any quoted or unquoted is misspelled
        for i in range(len(unquoted)):
            while unquoted[i] not in self._word_dict:
                print(self._find_closest(unquoted[i]))  # don't delete
                # get input
                user_input = raw_input("It seems that you misspelled \"%s\". Some suggestions are displayed above? \n"
                                   "Do you want to change your input for this word (y/n)" %unquoted[i])
                # user doesn't want to change their mind
                if user_input[0] == 'n':
                    break
                else:
                    # change user input
                    unquoted[i] = raw_input("To what? ")

        result_urls = self._match_and_rank_urls(quoted,unquoted,num_results)

        # url, page title, snippet
        out = ''
        for index in result_urls:
            url = self._urls[index]        
            title = ' '.join(re.findall(r'<title[^>]*>(.+?[^<]+)</title>', self._cached_pages[index], re.I))
            snip = self._snippet(index,quoted,unquoted)
            out += '<li><a href=\"%s\">%s</a> <br /> %s <br>' % (url,title,snip)
            out += '\n'


	return out

    # "private" function _parse_search_query
    # returns non-repeating desired search terms of each type (quoted and unquoted)
    def _parse_search_query(self,query):
        quoted = list(set(re.findall(r'"(.*?)"', query)))
        query = query.replace('"', '')
        # unquoted also includes quoted, but split up
        unquoted = list(set(query.split()))
        return quoted, unquoted

    # "private" function _find_closest()
    # from  the whole dictionary, returns a list of possible words that takes the least number of edits,
    # utilizing the min_edit algorithm in helper function _dist(), given the misspelled word
    def _find_closest(self, misspelled):
        edit_dist = [self._dist(misspelled, self._word_dict[i]) for i in range(len(self._word_dict))]
        min_edit = min(edit_dist)
        return [self._word_dict[i] for i in range(len(edit_dist)) if edit_dist[i] == min_edit]

    # "private" function _dist()
    # DP implementation of word edit, remove, insert, replace algorithm; simulating typos
    # returns the minimum edits from word1 to word2
    def _dist(self,word1, word2):
        n1 = len(word1)
        n2 = len(word2)

        # the minimum edit distance from word1[:i] to word2[:j]
        edit_distance = [[i for i in range(n2+1)] for j in range(n1+1)]

        for i in range(n1+1):
            for j in range(n2+1):
                # word1 is empty, insert one character at a time
                if i==0:
                    edit_distance[i][j] = j

                # word2 is empty, remove one character at a time
                elif j==0:
                    edit_distance[i][j] = i

                # last characters are the same, no edits necessary
                elif word1[i-1] == word2[j-1]:
                    edit_distance[i][j] = edit_distance[i-1][j-1]

                # last characters are different, take min of the edits and add 1 for the edit
                else:
                    edit_distance[i][j] = 1 + min(edit_distance[i][j-1],edit_distance[i-1][j],edit_distance[i-1][j-1])

        return edit_distance[n1][n2]

    # "private" function _match_and_rank_urls()
    # return ranked urls, grouped by number of relevant matches, in terms of indices
    def _match_and_rank_urls(self,quoted,unquoted,num_results):
        ranked_urls = []
        match_rank = [] # ranks in terms of matches
        indices = []

        quoted_pattern = '(' + '|'.join(quoted) + ')'
        n_quoted = len(quoted)

        unquoted_pattern = '(' + '|'.join(unquoted) + ')'
        n_unquoted = len(unquoted)

        n = self._N.shape[0]
        # find pages matching query
        for i in range(n):
            page = self._clean_cached_pages[i]
            if len(quoted) > 0:
                q = re.findall(quoted_pattern, page, re.I)
            else:
                q = []
            if len(unquoted) > 0:
                uq = re.findall(unquoted_pattern, page, re.I)
            else:
                uq = []
            # includes unique number of keyword matches
            if len(q)>0 or len(uq)>0:
                match_rank.append((i,len(set(q)),len(set(uq))))
                indices.append(i)

        # no results found
        if len(indices) == 0:
            return []

        # pagerank on subnetwork
        subnet = self._subnetwork(indices)
        index_dict = {indices[i]:i for i in range(len(indices))}
        popularity_rank = self._pagerank(subnet,0.01)   # ranks in term of PageRank algorithm

        # group results based on how many matches
        for n_exact in range(n_quoted,-2,-1):
            # get indices of segment
            segment = []
            if n_exact==0:
                segment = [tup[0] for tup in match_rank if tup[1] == 0 and tup[2] > n_unquoted/2]
            elif n_exact==-1:
                segment = [tup[0] for tup in match_rank if tup[1] == 0 and tup[2] <= n_unquoted/2]
            # if there are some exact matches, treat each page in the segment equally
            else:
                segment = [tup[0] for tup in match_rank if tup[1] == n_exact]

            # rank each url segment by PageRank
            segment.sort(key=lambda index: popularity_rank[index_dict[index]])
            ranked_urls += segment
            # stop getting results when we have enough
            if len(ranked_urls) > num_results:
                ranked_urls = ranked_urls[:num_results]
                break

        return ranked_urls

    # "private" function _subnetwork()
    # mxm subset of normal network with rows and columns indices in the input list indices
    def _subnetwork(self,indices):
        return [[self._N[r,c] for c in indices] for r in indices]

    # "private" function _pagerank()
    # returns rank of each page utilizing EVD version of PageRank algorithm
    def _pagerank(self,N,p):
        N = np.array(N, dtype=float)
        w,v = np.linalg.eig(self._normalize(N+p))
        w = abs(w)
        index = np.where(w==max(w))[0][0]
        scores = v[:,index]
        ranks = np.flipud(scores.argsort())
        return ranks

    # "private" helper function _normalize
    # normalize matrix by columns
    def _normalize(self,net):
        return net/net.sum(axis=0)

    # "private" function _snippet()
    # utilize moving window, display 2 to 3 lines of text of the "best" snippet, that with the most query occurrences
    def _snippet(self,index,quoted,unquoted):
        window = 300    # this arbitrary length makes the output look nice enough
        txt = self._clean_cached_pages[index]
        # page is really small, prints 2 lines
        if len(txt) < 300:
            words = txt.split()
            word_per_line = int(len(words) / 2 + 1)
            lines = [' '.join(words[i * word_per_line:(i + 1) * word_per_line]) for i in range(2)]
            return '\n'.join(lines)
        terms = quoted + unquoted
        pattern = '(' + '|'.join(terms) + ')'
        n_matches = [len(re.findall(pattern, txt[i:i+window], re.I)) for i in range(len(txt)-window)]
        max_i = n_matches.index(max(n_matches))
        best_txt = txt[max_i:max_i+window]

        # make it look nice by applying css word-wrap
	return '<div>%s</div>' % best_txt

    # "private" variables
    _N = np.array([[]], dtype=int)
    _urls = []
    _cached_pages = []
    _clean_cached_pages = []
    _url_index = {}
    _word_dict = {}

# helper print code taken from http://www.zackgrossbart.com/hackito/search-engine-python/

# This method will print out the results page incorporating
# the results from the search operation.
def doresultspage(terms = '', results = ''):
    for line in open("SearchResults.html", 'r'):
        if line.find("${SEARCH_RESULTS_GO_HERE}") != -1:
	    print "<div id=\"search_results\">\n<ol>"
	    if len(results) == 0:
		print "<h3>Your search did not return any results.</h3>"
	    print results
	    print "</ol>\n</div>\n"
        elif line.find("${SEARCH_TERMS_GO_HERE}") != -1:
            termindex = line.find("${SEARCH_TERMS_GO_HERE}")
            searchterms = "<span id=\"search_terms\">" + terms + "</span>\n"
            print line.replace("${SEARCH_TERMS_GO_HERE}", searchterms)
        else:
            print line



# scripts begin
form = cgi.FieldStorage()
results = []
terms = ''
urls = ''

import sys

try:
    if form.has_key("urls"):
        urls = form.getvalue("urls")
    else:
	print 'We\'re gonna need that internet to proceed'
    if form.has_key("query"):
        terms = form.getvalue("query")
    english_dict = urllib2.urlopen('http://mieliestronk.com/corncob_lowercase.txt').read().decode('utf-8').split()
    cool_engine = SearchEngine(urls,english_dict)
    results = cool_engine.query(terms, 10)
    doresultspage(terms, results)
except NameError:
    print "There was an error understanding your search request.  Please press the back button and try again."
except:
    print "Really Unexpected error:", sys.exc_info()[0]

    
