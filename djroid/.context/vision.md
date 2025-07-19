# DJroid Vision Context Document

A document for summarizing the overarching vision of the djroid application. 

## Objective
You are the lead agent in charge of the DJroid application. Your goal is to surmise context about the application from this document and others adjacent to it in order to answer questions relevant to the project and to contribute further to the codebase. The relevant documents (other than this one) you can inspect to gain further context are as follows:
- architecture.md for information on the architecture and technologies used in this project
- workflow.md for information on the desired workflow/user-experience of the application
- backlog.md to see currently tracked bugs or desired features that dont yet exist

These documents should be updated periodically to encompass the vision, target outcomes, architecture, and other key pieces of information that provide proper context to LLM's working with the djroid codebase. Below is a description of the vision of the project and relevant features/commands. Use these to create a foundational knowledge of the project at large, and then further inspect the other documents as you see fit to answer other questions you may have about the implementation of the project.

## Vision
DJroid is a DJ-centric cli toolsuite that provides DJs a way to interact with their archive of music files, giving them the ability to pass a prompt to the command line describing a certain criteria about the music they wish to play, and djroid generating a rekordbox-recognizable playlist using a combination of key-words from that prompt and internal algorithms/processes relating to the art and science of DJing.

## Features/Commands
- tag-scehma: create a tag-schema of custom categories/values that can be used to describe their music
- tag: tag their audio files (mp3/aiff) with the custom tag-schema values, tying these values to the metadata of the audio file
- scan: recurse their archive of music and update or generate an internal database using the metadata of the song files processed
- crate: convert a passed-in prompt from the user into a series of queries that provide a list of songs meeting the criteria of that prompt 