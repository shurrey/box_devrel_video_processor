Field | Type | Description 
---|---|---
topic | Text | Based on the contents of the file, identify the main topic of the transcript. Limit the topic to 60 characters or less. If you can't identify a value, return "unknown" 
speakers | Text | Who are the speakers for this transcript?  If you can't identify a value, return "Unknown" 
provider | Text | Who is the model provider for this video. Examples include OpenAI, Google, Azure, AWS, IBM, etc.  If you can't identify a value, return "unknown"
model | Text | what large language model is being used. Examples are GPT 5, Claude 4 Sonnet, Gemini 2.5 Pro.  If you can't identify a value, return "unknown"
title | Text | Propose a catchy title for the video. Should be short, but generate excitement and make people want to watch the video.  If you can't identify a value, return "unknown"
tags | Text | comma-separated tags for this transcript. These tags will be used to help people find the video on youtube, examples are ai, developer, ai agents, mcp server, etc. Do not provide more than 20 tags.  If you can't identify a value, return "unknown"
technologies | Text | comma-seperated list of the technologies in this transcript. Examples are Pydantic, LangChain, LlamaIndex, OpenAI, Anthropic, Claude, Gemini, Vertex, MCP, A2A, ADK.  If you can't identify a value, return "unknown"