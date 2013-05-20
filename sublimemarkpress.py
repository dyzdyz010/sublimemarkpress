# coding=utf-8
import sublime, sublime_plugin # sublime
import sys
reload(sys)
sys.setdefaultencoding( "utf-8" )
class PublishCommand(sublime_plugin.TextCommand):
	r""" 
		** Pushes the curent active file to a metaweblog compatible blog **

		# blog settings
		Relies on a settings file called "sublimemarkpress.sublime-settings" using the structure:
			{
			    "xmlrpcurl": <URL to xml rpc endpoint>,
			    "username": <username>,
			    "password": <password>
			}

		# tags
		blog tags are optional at the top of the file in the structure:
		<!-- 
		#post_id:<id of existing post - optional>
		#tags:<comma delimited list of post tags - optional>
		#status:<draft or publish - optional, draft by default>
		#categories:<comma delimited list of post categories - optional>
		#title:<title of the post - optional>
		#markdown:<"true" or "false" - if the post use markdown layout - optional, false by default>
		-->

		# markdown
		**Two options: **
		1. If the file "markdown2.py" from the awesome repo https://github.com/trentm/python-markdown2/tree/master/lib exists, markdown is enabled
		2. If the package "Python Markdown" installed in the plugin's path, markdown is enabled. Attention:build the plugin manually every time you restart the ST.
	"""
	def run(self, edit):
		# get page content
		all_lines_in_page = self.view.lines(sublime.Region(0, self.view.size()))
		header_lines = []
		
		# get the "header" (MB details)
		post_id, tags, status, categories, title, is_markdown, has_header_content = self.GetHeaderContent(all_lines_in_page, header_lines)

		# get the "body" (content)
		post_content = self.GetPostContent(self.view,all_lines_in_page, is_markdown)

		# create request
		content = self.BuildPostContent(self.view, {"content": post_content, "title": title, "tags": tags, "status": status, "categories":categories})

		# save to MB
		new_post, post_id = self.SaveToMetaWeblog(self.view, edit, post_id, self.LoadMetaBlogSettings(), content)

		#  update active window with post id, if new
		if new_post:
			self.PrefixPostHeader(self.view, edit, post_id, header_lines, has_header_content)

	def LoadMetaBlogSettings(self):
		s = sublime.load_settings("sublimemarkpress.sublime-settings")
		return {"url": s.get("xmlrpcurl"), "username": s.get("username"), "password": s.get("password")}

	def GetHeaderContent(self, all_lines_in_page, header_lines):
		page_info = {"has_header_content":False, "post_id":None, "tags":"", "status":"draft", "categories":[], "title":"", "markdown":False}

		if self.view.substr(all_lines_in_page[0]).startswith("<!--"):
			page_info["has_header_content"] = True
			self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			# post_id
			if self.view.substr(all_lines_in_page[0]).startswith("#post_id"):
				page_info["post_id"] = self.view.substr(all_lines_in_page[0]).split(":")[1]
				self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			# post tags
			if self.view.substr(all_lines_in_page[0]).startswith("#tags"):
				page_info["tags"] = self.view.substr(all_lines_in_page[0]).split(":")[1]
				self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			# post status
			if self.view.substr(all_lines_in_page[0]).startswith("#status"):
				page_info["status"] = self.view.substr(all_lines_in_page[0]).split(":")[1]
				self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			# categories
			if self.view.substr(all_lines_in_page[0]).startswith("#categories"):
				page_info["categories"] = self.view.substr(all_lines_in_page[0]).split(":")[1].split(",")
				self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			# title
			if self.view.substr(all_lines_in_page[0]).startswith("#title"):
				page_info["title"] = self.view.substr(all_lines_in_page[0]).split(":")[1]
				self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			# markdown
			if self.view.substr(all_lines_in_page[0]).startswith("#markdown"):
				if self.view.substr(all_lines_in_page[0]).split(":")[1] == "true":
					page_info["markdown"] = True
				self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

			self.MoveCurrentLineToHeader(header_lines, all_lines_in_page) # removes the closing comment tag

		return page_info["post_id"], page_info["tags"], page_info["status"], page_info["categories"], page_info["title"], page_info["markdown"], page_info["has_header_content"]

	def GetTitle(self, view, all_lines_in_page, header_lines):
		is_markdown = False
		if self.view.substr(all_lines_in_page[0]).startswith("# "):
			title = self.view.substr(all_lines_in_page[0]).split("# ")[1]
			is_markdown = True
		else:
			title = self.view.substr(all_lines_in_page[0])
		
		# remove the title from the content (else it'll get repeated within the content)		
		self.MoveCurrentLineToHeader(header_lines, all_lines_in_page)

		return title, is_markdown

	def GetPostContent(self, view, all_lines_in_page, is_markdown):
		post_content = self.CombineContent(self.view, all_lines_in_page)

		can_markdown = False
		is_markdown2, is_python_markdown = False, False
		try: 
			import markdown # python markdown
			can_markdown = True
			is_python_markdown = True
		except ImportError:
			can_markdown = False

		try: 
			import markdown2 # markdown2
			can_markdown = True
			is_markdown2 = True
		except ImportError:
			can_markdown = False

		# markdown content
		if is_markdown and can_markdown:
			if is_python_markdown:
				post_content = markdown.markdown(post_content, extensions=['codehilite'])
			else:
				post_content = str(markdown2.markdown(post_content, extras=["code-friendly"]))

		return post_content

	def MoveCurrentLineToHeader(self, header_lines, all_lines_in_page):
			header_lines.insert(len(header_lines),all_lines_in_page[0])
			all_lines_in_page.remove(all_lines_in_page[0])

	def BuildPostContent(self, view, page_data):		
		return {"description": page_data["content"], "post_content": page_data["content"], "title": page_data["title"], "mt_keywords": page_data["tags"], "categories": page_data["categories"], "post_status": page_data["status"]}

	def CombineContent(self, view, lines):
		return view.substr(sublime.Region(lines[0].begin(),lines[len(lines)-1].end()))

	def PrefixPostHeader(self, view, edit, post_id, header_lines, has_header):
		post_header = "<!--" + '\n' + "#post_id:" + str(post_id) + '\n'

		if has_header:
			end_point = header_lines[1].begin()
			header_lines.remove(header_lines[0])
			view.replace(edit, sublime.Region(0, end_point), post_header)
		else:
			view.replace(edit, sublime.Region(0,0), post_header + "-->" + '\n')

	def SaveToMetaWeblog(self, view, edit, post_id, blog_settings, content):
		import xmlrpclib # wordpress

		updated = False

		proxy = xmlrpclib.ServerProxy(blog_settings["url"])
		if post_id == None:
			blog_id = 0 # not currently used on wordpress
			post_id = proxy.metaWeblog.newPost(str(blog_id), blog_settings["username"], blog_settings["password"], content)
			updated = True
			print("created new:", post_id)
		else:
			proxy.metaWeblog.editPost(post_id, blog_settings["username"], blog_settings["password"], content)
			print("updated existing:", post_id)
		print("created new:", post_id)

		return updated, post_id
