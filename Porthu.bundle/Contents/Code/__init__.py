#Port.hu metadata agent for Plex Media Server
#Created by Sandor Juhasz
#Contact: blackghost1987@gmail.com

import re

PORTHU_SEARCH = 'http://www.port.hu/pls/ci/cinema.film_creator?i_text=%s&i_film_creator=1'
PORTHU_LIST = 'http://www.port.hu/pls/ci/films.film_list?i_text=%s&i_page=%s'
PORTHU_MOVIE = 'http://www.port.hu/pls/fi/films.film_page?i_film_id=%s'
IMDB_RELEASEINFO = 'http://www.imdb.com/title/%s/releaseinfo'

def Start():
  Log("Port.hu agent started")

class PorthuAgent(Agent.Movies):
  name = 'Porthu'
  languages = [Locale.Language.English]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']
  
  def calculateScore(self, media, port_id):
    url = PORTHU_MOVIE % (port_id)
    port_info_element = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    
    score = 0
    
    info_line_search = port_info_element.cssselect('td[width="98%"][valign="top"]')
    if len(info_line_search)>0:
      if (info_line_search[0].find('span') is not None):
        info_line = info_line_search[0].find('span').text_content()
        
        year_search = re.search(r"\d{4}",info_line)
        if year_search is not None:
          try:
            year = int(year_search.group())
          except ValueError:
            year = 0
          year_dist = abs(year - media.primary_metadata.year)
          score = 100-year_dist*7
        else:
          #No year information
          score = 80
        
        #check duration difference if duration is set
        if (media.primary_metadata.duration is not None):
          duration_search = re.search(r", \d* perc",info_line)
          if duration_search is not None:
            duration_str = duration_search.group()[2:-5]
            try:
              duration = float(duration_str)
            except ValueError:
              duration = 0
            duration_dist = abs(duration*60000 - media.primary_metadata.duration)/60000
            score = score - duration_dist
      else:
        #No info line
        score = 60
    else:
      #No info line
      score = 60
      
    return score
      
  def searchPorthu(self, results, media, title, hungarian):
    #Searching for the IMDB title in the Port.hu database
    Log("Searching for IMDB ID: %s with title: %s" % (media.primary_metadata.id,title))
    
    url = PORTHU_SEARCH % (String.Quote(title,True))
    port_info_element = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    wrapper = port_info_element.get_element_by_id('film_list_wrapper',"-")
    
    good_match = False
    
    #check if multiple result or direct match
    if wrapper != "-":
      #multiple result, getting result pages
      lastpage = 0
      for pagelink in wrapper.getparent().cssselect('span[class="txt"] a[class="bodlink"]'):
        pagenum_search = re.search(r"i_page=\d*&",pagelink.attrib['href'])
        if pagenum_search is not None:
          pagenumstr = pagenum_search.group()[7:-1]
          try:
            pagenum = int(pagenumstr)
          except ValueError:
            pagenum = 0
          if pagenum > lastpage:
            lastpage=pagenum
      #for end
      
      #Log("Total page num: %d" % lastpage)
      
      #Searching for the title over all of the pages
      actual_page = 0
      while actual_page<=lastpage and good_match==False:
      
        if actual_page!=0:
          #Log("Checking page: %d" % actual_page)
          url = PORTHU_LIST % (String.Quote(title,True),actual_page)
          port_info_element = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
          wrapper = port_info_element.get_element_by_id('film_list_wrapper',"-")
    
        if wrapper != "-":
      
          for match in wrapper.cssselect('span[class="btxt"]'):
          
            #check if channel line (has a txt after btxt)
            if (match.getnext() is not None):
          
              full_title = match.text_content()
              orig_title_search = re.findall(r"\([^(]*\)",full_title)
              if len(orig_title_search)>0:
                #has original title
                if (hungarian):
                  #lets check if there's a hungarian title too
                  hun_title_search = re.findall(r".+\(",full_title)
                  if len(hun_title_search)>0:
                    port_title = hun_title_search[0][:-2]
                  else:
                    #just get the original title
                    port_title = orig_title_search[-1][1:-1]
                  
                else:
                  #just get the original title
                  port_title = orig_title_search[-1][1:-1]
                  
              else:
                #no original title, lets check full title
                port_title = full_title[1:]

              #Log("selected title: **%s**" % port_title)
              
              if (port_title != ""):
                
                strDist = String.LevenshteinDistance(port_title.lower(),title.lower());
                
                #check if the selected title has multiple parts (separated by /)
                if (re.match(r".*/",port_title) is not None):
                  #Log(" / in the original title, splitting...")
                  splits = re.split(r"/",port_title)
                  for part in splits:
                    #Log("part: %s" % part)
                    strDistAlt = String.LevenshteinDistance(part.lower(),title.lower());
                    if strDistAlt < strDist:
                      strDist = strDistAlt
                
                if strDist < 5:
                  
                  score = (-5)*strDist
                  
                  #Title matched, let's check the year and duration
                  
                  movie_link = match.find('a').attrib['href']
                  id_search = re.search(r"film_id=\d*&",movie_link)
                  if id_search is not None:
                    port_id = id_search.group()[8:-1]
                  
                    score = score + self.calculateScore(media, port_id)
                  
                    Log("Adding a match with port ID: %s" % port_id)
                    results.Append(MetadataSearchResult(id = media.primary_metadata.id+"=>"+port_id, score = score))
                    if score >= 90:
                      good_match = True
                      Log("Good match, ending search with this page")
                      
                  #if portID found - end
                #if strdist - end
              #if title empty - end
            #if channel line
          #for end
        #if wrapper - end
        actual_page+=1
      #while end
          
    else:
      #No match or direct match, lets check
      
      port_title=""
      
      if (hungarian):
        port_headers = port_info_element.cssselect('h1[class="blackbigtitle"]')
        if len(port_headers)>0:
          port_title = port_headers[0].text_content()
          if port_title[:1] == "(":
            port_title = port_title[1:-1]
            Log("Direct match, but no hungarian title. Original title: %s" % port_title)
          else:
            Log("Direct match, Port.hu title: %s" % port_title)
        #else no match
      else:
        port_headers = port_info_element.cssselect('h2[class="txt"]')
        if len(port_headers)>0:
          port_title = port_headers[0].text_content()[1:-1]
          Log("Direct match, Port.hu title: %s" % port_title)
        else:
          #No match or no hungarian title
          hastitle = port_info_element.cssselect('h1[class="blackbigtitle"]')
          if len(hastitle)>0:
            port_title = hastitle[0].text_content()
            if port_title[:1] == "(":
              port_title = port_title[1:-1]
            Log("Direct match, but no hungarian title. Original title: %s" % port_title)
          #else no match
      
      if (port_title != ""):
      
        strDist = String.LevenshteinDistance(port_title.lower(),title.lower());
      
        #check if the selected title has multiple parts (separated by /)
        if (re.match(r".*/",port_title) is not None):
          #Log(" / in the original title, splitting...")
          splits = re.split(r"/",port_title)
          for part in splits:
            #Log("part: %s" % part)
            strDistAlt = String.LevenshteinDistance(part.lower(),title.lower());
            if strDistAlt < strDist:
              strDist = strDistAlt

        
        if strDist < 5:

          score = (-5)*strDist

          #Title matched, let's check the year and duration
          
          port_links = port_info_element.cssselect('link[rel="canonical"]')
          if len(port_links)>0:
            movie_link = port_links[0].attrib['href']
            id_search = re.search(r"film_id=\d*$",movie_link)
            if id_search is not None:
              port_id = id_search.group()[8:]
              
              score = score + self.calculateScore(media, port_id)
              
              #Log("Appending from direct match")
              results.Append(MetadataSearchResult(id = media.primary_metadata.id+"=>"+port_id, score = score))
              good_match = True
          #else can't determine Port ID (no canonical link on the direct match page)
      #end if title empty
    #end if direct match  
    return good_match
  
  def getMainTitleFromIMDB(self, IMDB_ID):
    url = IMDB_RELEASEINFO % IMDB_ID
    imdb_releaseinfo = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    
    imdb_title = imdb_releaseinfo.cssselect('span.title-extra')
    if len(imdb_title)>0:
      if (len(imdb_title[0].text_content())>0):
        return imdb_title[0].text_content()[:-17]
      #else get main title
    
    imdb_title = imdb_releaseinfo.cssselect('a.main')
    if len(imdb_title)>0:
      return imdb_title[0].text_content()
      
    return None
    
  def getForeignTitleFromIMDB(self, search_country, IMDB_ID):
    url = IMDB_RELEASEINFO % IMDB_ID
    #Log("imdb releaseinfo url: %s" % url)
    imdb_releaseinfo = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    title_trs = imdb_releaseinfo.cssselect('#tn15content h5+table tr')
    for title_tr in title_trs:
        children = title_tr.getchildren()
        title = children[0].text_content()
        country = children[1].text_content()
        #Log("title: %s ; country: %s" % (title,country))
        if re.search(search_country,country,re.IGNORECASE) is not None:
          return title
    #end for
    return None
  
  def search(self, results, media, lang, manual=False):
    if media.primary_metadata is None:
      Log("No IMDB match, can't do anything")
      return
    
    Log("Searching for IMDB english title: %s" % media.primary_metadata.title)
    if self.searchPorthu(results, media, media.primary_metadata.title, False):
      return
    
    title = re.sub(r"[\.,:;/\?!-]","",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchPorthu(results, media, title, False):
        return
    
    title = re.sub(r"[\.,:;/\?!-]"," ",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchPorthu(results, media, title, False):
        return
    
    title = re.sub(r"&","and",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchPorthu(results, media, title, False):
        return
    
    title = re.sub(r"&"," and ",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchPorthu(results, media, title, False):
        return
    
    title = re.sub(r"and","&",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchPorthu(results, media, title, False):
        return
    
    Log("No good match found with englis title, trying to get hungarian title from IMDB")
    hun_title = self.getForeignTitleFromIMDB("Hungary",media.primary_metadata.id)
    if (hun_title is not None):
      
      if self.searchPorthu(results, media, hun_title, True):
        return
      
      title = re.sub(r"[\.,:;/\?!-]","",hun_title)
      if title!=hun_title:
        if self.searchPorthu(results, media, title, True):
          return
      
      title = re.sub(r"[\.,:;/\?!-]"," ",hun_title)
      if title!=hun_title:
        if self.searchPorthu(results, media, title, True):
          return
      
      Log("No good match found on Port.hu, adding hungarian title at least")
      results.Append(MetadataSearchResult(id = media.primary_metadata.id+"=>0", score = 100))
      return
      #ending with hungarian title only
      
    else:
    
      Log("Hungarian title not found, trying to get the original title from IMDB")
      orig_title = self.getMainTitleFromIMDB(media.primary_metadata.id)
      if (orig_title is not None):
        #Log("original title: %s" % orig_title)
        if self.searchPorthu(results, media, orig_title, False):
          return
          
        title = re.sub(r"[\.,:;/\?!-]","",orig_title)
        if title!=orig_title:
          if self.searchPorthu(results, media, title, False):
            return
          
        title = re.sub(r"[\.,:;/\?!-]"," ",orig_title)
        if title!=orig_title:
          if self.searchPorthu(results, media, title, False):
            return
          
      #end if orig_title  
      
      Log("No match with original title, trying with other titles from country list")
    
      for country in media.primary_metadata.countries:
        Log("Searching title from country: %s" % country)
        orig_title = self.getForeignTitleFromIMDB(country,media.primary_metadata.id)
        if (orig_title is not None):
          Log("Original title might be: %s" % orig_title)
          if self.searchPorthu(results, media, orig_title, False):
            return
          
          title = re.sub(r"[\.,:;/\?!-]","",orig_title)
          if title!=orig_title:
            if self.searchPorthu(results, media, title, False):
              return
            
          title = re.sub(r"[\.,:;/\?!-]"," ",orig_title)
          if title!=orig_title:
            if self.searchPorthu(results, media, title, False):
              return
      #for end
  
    Log("No Port.hu match found, giving up")
       
  def update(self, metadata, media, lang):
    both_id = re.split("=>",metadata.id)
    imdb_id = both_id[0]
    #Log("imdb_id: %s " % imdb_id)
    port_id = both_id[1]
    
    if (port_id != "0"):
      
      Log("Updating data for port ID: %s" % (port_id))
        
      url = PORTHU_MOVIE % (port_id)
      port_info_element = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
      
      #getting the titles
      port_title = port_info_element.cssselect('h1[class="blackbigtitle"]')[0].text_content()
      if port_title[:1] == "(":
        #Log("No hungarian title found on Port.hu")
        imdb_hun_title = self.getForeignTitleFromIMDB("Hungary",imdb_id)
        if (imdb_hun_title is not None):
          metadata.title = imdb_hun_title
          orig_title = self.getMainTitleFromIMDB(imdb_id)
          if (orig_title is not None):
            #Log("adding orig_title: %s" % orig_title)
            metadata.original_title = orig_title
          #else No english title found on IMDB
        #else No hungarian title found on IMDB either
      else:
        metadata.title = port_title
        Log("Title by Port.hu: %s" % port_title)
        port_headers = port_info_element.cssselect('h2[class="txt"]')
        if len(port_headers)>0:
          orig_title = port_headers[0].text_content()[1:-1]
          #Log("Original title: %s" % orig_title)
          metadata.original_title = orig_title
        else:
          Log("Title is the same as the original title")
          metadata.original_title = port_title
        
      #getting the summary
      summary_search = port_info_element.cssselect('td[colspan="2"][align="left"]')
      summary = summary_search[0].text_content()[2:]
      airdate_search = re.search(r"Bemut",summary)
      if airdate_search is not None:
        summary = summary[:airdate_search.start()]
      if len(summary)>2:
        Log("Movie summary found")
        metadata.summary = summary
      else:
        Log("No summary found")
        
    else:
      Log("No Port.hu match, adding the hungarian IMDB title")
      imdb_hun_title = self.getForeignTitleFromIMDB("Hungary",imdb_id)
      if (imdb_hun_title is not None):
        metadata.title = imdb_hun_title
        
    Log("Metadata update finished")