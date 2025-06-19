# Personal Knowledge Graph
## Project Overview:

1.  Use Brightspace API and user credentials to get course contents
    1. Identify relevant API endpoints
        1. List of courses user is enrolled in
        2. Content structure of a specific course
        3. Details about a specific topic and its contents
    2. Address security concerns
        1. Use secure authentication methods like OAuth 2.0
2.  Identify topics and subtopics based on course contents
    1. Processing
        1. spaCy for text pre-processing
        2. Gensim API for topic modeling tools
    2. Content type
        1. PDF
        2. HTML
        3. link to website
        4. Code (primarily java for now)
4.  Create topic and subtopic nodes
5.  Generate tests relevant to each topic node
    1. Quiz
        1. True or false
        2. Multiple choice
        3. Fill in the blanks
        4. Short answer
    2. Coding challenges
6.  Set forgetting curve timer
    1. Exponential increase
7.  Prompt user to take test again once timer approaches zero
    1. Notification System

## Potential features:
1. [[Interactive 3D graph]]
    1. Identify and create relationships between nodes
