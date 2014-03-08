#Filmkatalogus metadata agent for Plex Media Server
#Created by Sandor Juhasz
#Contact: blackghost1987@gmail.com

import re

FILMKATALOGUS_SEARCH = 'http://www.filmkatalogus.hu/kereses'
FILMKATALOGUS_LIST = 'http://www.filmkatalogus.hu/osszestalalat-f-'
FILMKATALOGUS_MOVIE = 'http://www.filmkatalogus.hu/'
IMDB_RELEASEINFO = 'http://www.imdb.com/title/%s/releaseinfo'
IMDB_MAIN = 'http://www.imdb.com/title/%s/'

def Start():
  Log("Filmkatalogus agent started")

class FilmkatalogusAgent(Agent.Movies):
  name = 'Filmkatalogus'
  languages = [Locale.Language.English]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']
  
  def calculateFilmkatalogusScore(self, media, filmkatalogus_id):
    url = FILMKATALOGUS_MOVIE + filmkatalogus_id
    page = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    
    score = 100
    
    if (media.primary_metadata.year) is not None:
    
      h2 = page.cssselect('h2')
      
      if len(h2)>0:
        info_line=h2[0].text_content()
        #Log("ino_line: %s" % info_line)
        year_search = re.findall(r"\d{4}\)$",info_line)
        if len(year_search)>0:
          try:
            year = int(year_search[0][:-1])
          except ValueError:
            year = 0
            
          year_dist = abs(year - media.primary_metadata.year)
          score = score-year_dist*7
          #Log("score based on year: %s" % score)
        else:
          Log("No year information")
          score = score - 15
      else:    
        Log("No info line")
        score = 80
    else:
      Log("No year info from IMDB")
    
    return score
  
  def searchFilmkatalogus(self, results, media, title, hungarian):
    
    #Searching for the IMDB title in the Filmkatalogus database
    Log("Searching for IMDB ID: %s with title: %s" % (media.primary_metadata.id,title))
    
    good_match = False

    url = FILMKATALOGUS_LIST + String.Quote(title,True)
    page = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    error = page.cssselect('.hiba')
    
    if len(error)>1:
      Log("No match, error message: %s", error[1].text_content())
      Log("Trying direct search with title: %s", title)
    
      url = FILMKATALOGUS_SEARCH
      values = { 'szo1': title , 'ment': 1, 'keres1': 1, 'sbmt': 'Keresés filmek között'}
      page = HTML.ElementFromURL(url,values,cacheTime=3600,timeout=10.0)
      
      error = page.cssselect('.hiba')
    
    if len(error)>1:
      Log("Still no match, error message: %s", error[1].text_content())
      
    movie = page.get_element_by_id('film1',"-")
      
    #check if multiple result or direct match
    if movie == "-":
      matches = page.cssselect('.tabla2')
      #Log("Multiple result, count: %s",len(matches))
      
      for match in matches:
        tds = match.findall('td')
        if len(tds)==3:
          if tds[0].find('b') is None:
            cell = tds[0][0]
            
            if 'title' not in cell.attrib:
              cell = tds[0][1]
              
            #Log("cell content: %s", cell.text_content())
            hun_title = cell.text_content()
            if (cell.tail):
              if len(cell.tail)>7:
                orig_title = cell.tail[8:-1]
              else:
                orig_title = hun_title
            else:
              orig_title = hun_title
            movie_link = cell.attrib['href']
                        
            #Log("hun title: **%s**" % hun_title)
            #Log("orig title: **%s**" % orig_title)
            
            if len(orig_title)>0:
              if (hungarian):
                #use the hungarian title
                selected_title = hun_title
              else:
                #use the original title
                selected_title = orig_title
                
            else:
              #use the hungarian title")
              selected_title = hun_title

            #Log("selected title: **%s**, searched title: **%s**" % (selected_title,title))
            
            strDist = String.LevenshteinDistance(selected_title.lower(),title.lower());
            if strDist < 5:
              
              score = (-3)*strDist
              
              #Title matched, let's check the year and duration
              
              #Log("link: **%s**" % movie_link)
              id_search = re.findall(r"--f\d*$",movie_link)
              if len(id_search)>0:
                filmkatalogus_id = id_search[0][2:]
              
                #Log("filmkatalogus id: **%s**" % filmkatalogus_id)
              
                score = score + self.calculateFilmkatalogusScore(media, filmkatalogus_id)
                  
                Log("Adding a match with filmkatalogus ID: %s (score: %s)" % (filmkatalogus_id,score))
                results.Append(MetadataSearchResult(id = media.primary_metadata.id+"=>"+filmkatalogus_id, score = score))
                if score >= 90:
                  good_match = True
                  Log("Good match found, stopping the search")
                  break
                  
              #if ID found - end
            #if strdist - end
          #else a series
        #else the header
      #for end    
    else:
      Log("direct match")
      h1 = page.cssselect('h1')
      h2 = page.cssselect('h2')
        
      
      hun_title = h1[0].text_content()
      
      if len(h2)>0:
        orig_title = h2[0].text_content()[1:-7]
      else:
        orig_title = hun_title

      #Log("hun title: **%s**" % hun_title)
      #Log("orig title: **%s**" % orig_title)
      
      if len(orig_title)>0:
        if (hungarian):
          #use the hungarian title
          selected_title = hun_title
        else:
          #use the original title
          selected_title = orig_title
          
      else:
        #use the hungarian title")
        selected_title = hun_title

      #Log("selected title: **%s**, searched title: **%s**" % (selected_title,title))
        
      strDist = String.LevenshteinDistance(selected_title.lower(),title.lower());
      if strDist < 5:
        
        score = (-3)*strDist
        
        #Title matched, let's check the year and duration
        
        checkbox = page.cssselect('.checkbox')
        
        if len(checkbox)>0:
          
          movie_link = checkbox[0].attrib['onclick']
          
          id_search = re.findall(r"-f\d*\";$",movie_link)
          if len(id_search)>0:
            filmkatalogus_id = id_search[0][1:-2]
            score = score + self.calculateFilmkatalogusScore(media, filmkatalogus_id)
            
            Log("Adding a direct match with filmkatalogus ID: %s (score: %s)" % (filmkatalogus_id,score))
            results.Append(MetadataSearchResult(id = media.primary_metadata.id+"=>"+filmkatalogus_id, score = score))
            if score >= 90:
              good_match = True
          #if id not found
        #if checkbox found - end
      #if strdist - end

    Log("Search finished")
    return good_match
  
  def getMainTitleFromIMDB(self, IMDB_ID):
    url = IMDB_MAIN % IMDB_ID
    imdb_releaseinfo = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    
    imdb_title = imdb_releaseinfo.cssselect('span.title-extra')
    if len(imdb_title)>0:
      if (len(imdb_title[0].text_content())>0):
        return imdb_title[0].text_content().strip()[:-17].strip()[1:-1]
      #else get main title
    
    imdb_title = imdb_releaseinfo.cssselect('a.main')
    if len(imdb_title)>0:
      return imdb_title[0].text_content()
      
    return None
    
  def getForeignTitleFromIMDB(self, search_country, IMDB_ID):
    url = IMDB_RELEASEINFO % IMDB_ID
    #Log("imdb releaseinfo url: %s" % url)
    imdb_releaseinfo = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
    title_trs = imdb_releaseinfo.cssselect('#akas tr')
    for title_tr in title_trs:
        children = title_tr.getchildren()
        country = children[0].text_content()
        title = children[1].text_content()
        #Log("title: %s ; country: %s" % (title,country))
        if re.search(search_country,country,re.IGNORECASE) is not None:
          return title
    #end for
    return None
  
  def search(self, results, media, lang, manual=False):
  
    if media.primary_metadata is None:
      Log("No IMDB match, can't do anything")
      return
    
    Log("Searching Filmkatalogus for IMDB english title: %s" % media.primary_metadata.title)
    if self.searchFilmkatalogus(results, media, media.primary_metadata.title, False):
      return
    
    title = re.sub(r"[\.,:;/\?!-]","",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchFilmkatalogus(results, media, title, False):
        return
    
    title = re.sub(r"[\.,:;/\?!-]"," ",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchFilmkatalogus(results, media, title, False):
        return
    
    title = re.sub(r"&","and",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchFilmkatalogus(results, media, title, False):
        return
    
    title = re.sub(r"&"," and ",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchFilmkatalogus(results, media, title, False):
        return
    
    title = re.sub(r"and","&",media.primary_metadata.title)
    if title!=media.primary_metadata.title:
      if self.searchFilmkatalogus(results, media, title, False):
        return
    
    Log("No good match found with englis title, trying to get hungarian title from IMDB")
    hun_title = self.getForeignTitleFromIMDB("Hungary",media.primary_metadata.id)
    if (hun_title is not None):
      
      if self.searchFilmkatalogus(results, media, hun_title, True):
        return
      
      title = re.sub(r"[\.,:;/\?!-]","",hun_title)
      if title!=hun_title:
        if self.searchFilmkatalogus(results, media, title, True):
          return
      
      title = re.sub(r"[\.,:;/\?!-]"," ",hun_title)
      if title!=hun_title:
        if self.searchFilmkatalogus(results, media, title, True):
          return
      
      Log("No good match found on Filmkatalogus, adding hungarian title at least")
      results.Append(MetadataSearchResult(id = media.primary_metadata.id+"=>0", score = 90))
    else:
      Log("Hungarian title not found")
    
    Log("Trying to get the original title from IMDB")
    orig_title = self.getMainTitleFromIMDB(media.primary_metadata.id)
    if (orig_title is not None):
      #Log("original title: %s" % orig_title)
      if self.searchFilmkatalogus(results, media, orig_title, False):
        return
        
      title = re.sub(r"[\.,:;/\?!-]","",orig_title)
      if title!=orig_title:
        if self.searchFilmkatalogus(results, media, title, False):
          return
        
      title = re.sub(r"[\.,:;/\?!-]"," ",orig_title)
      if title!=orig_title:
        if self.searchFilmkatalogus(results, media, title, False):
          return
      
    Log("No match with original title, trying with other titles from country list")
  
    for country in media.primary_metadata.countries:
      Log("Searching title from country: %s" % country)
      orig_title = self.getForeignTitleFromIMDB(country,media.primary_metadata.id)
      if (orig_title is not None):
        Log("Original title might be: %s" % orig_title)
        if self.searchFilmkatalogus(results, media, orig_title, False):
          return
        
        title = re.sub(r"[\.,:;/\?!-]","",orig_title)
        if title!=orig_title:
          if self.searchFilmkatalogus(results, media, title, False):
            return
          
        title = re.sub(r"[\.,:;/\?!-]"," ",orig_title)
        if title!=orig_title:
          if self.searchFilmkatalogus(results, media, title, False):
            return
    #for end
  
    Log("No Filmkatalogus match found, giving up")
   
  def update(self, metadata, media, lang):
    both_id = re.split("=>",metadata.id)
    imdb_id = both_id[0]
    #Log("imdb_id: %s " % imdb_id)
    filmkatalogus_id = both_id[1]
    
    if (filmkatalogus_id != "0"):
      
      Log("Updating data for filmkatalogus ID: %s" % (filmkatalogus_id))
      
      url = FILMKATALOGUS_MOVIE + filmkatalogus_id
      page = HTML.ElementFromURL(url,cacheTime=3600,timeout=10.0)
      
      h1 = page.cssselect('h1')
      h2 = page.cssselect('h2')

      hun_title = h1[0].text_content()
      
      if len(h2)>0:
        if len(h2[0].text_content())>8:
          orig_title = h2[0].text_content()[1:-7]
        else:
          orig_title = hun_title
          hun_title = ""
      else:
        orig_title = hun_title
        hun_title = ""

      #Log("hun title: **%s**" % hun_title)
      #Log("orig title: **%s**" % orig_title)
      
      if len(hun_title)>0:
        metadata.title = hun_title
        metadata.original_title = orig_title
      else:
        Log("No hungarian title -> titles are not modified")
      
      #getting the summary
      summary_div = page.cssselect('div[align=JUSTIFY]')
      if len(summary_div)>0:
        Log("Movie summary found")
        metadata.summary = summary_div[0].text_content()
      else:
        Log("No summary found")
        
    else:
      Log("No Filmkatalogus match, adding the hungarian IMDB title")
      imdb_hun_title = self.getForeignTitleFromIMDB("Hungary",imdb_id)
      if (imdb_hun_title is not None):
        metadata.title = imdb_hun_title
        
    Log("Metadata update finished")
