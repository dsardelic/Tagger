# Tagger

## What is Tagger?

Tagger is a simple web application for assigning tags to file and folder paths, and searching tagged elements based on an arbitrary selection of tags.

## Why would I use it?

For instance, let's say you have a large collection of movies. They may be organized into several subfolders based on their  _primary_  genre. One day your partner asks you to watch a movie together. Your partner would like to watch a comedy, but, since this person is easily scared, doesn't want a comedy with elements of horror in it. If only there was a way to search for a set of movies with specific desired traits... Well hello, Tagger!

## Is it something unique?

No, plenty of software can be found that does pretty much the same thing. However, some of the other solutions are not freeware, some don't enable tagging of files **and** folders, and some are way too complicated and have a plethora of features that are unnecessary for basic use. I used to use [Tabbles](https://tabbles.net), but it was just too big and simply ran too slow. At one point I stumbled upon another [file-tagger](https://sourceforge.net/projects/file-tagger/) which I haven't tried out, but which seems to cover the same use cases.

## How does it work?

Tagger is a Python (3.11) web application created using the Django (3.0.2) framework. It uses a simple JSON document-oriented database written in Python called [TinyDB](http://tinydb.readthedocs.io) to store all tag and mapping data. The software requirements can be found in a [separate file](requirements.txt).

## How do I use it?

Before running the application check out the [Tagger.ini](Tagger.ini) file in order to:
* Name an optional absolute path to the JSON file to be used as a database. The default database file is [TaggerDB.json](TaggerDB.json) in the project's root folder, i.e. the folder in which Tagger.ini resides. A sample pre-filled database is already provided. Feel free to delete it. If no file exists in the default or user-selected location, an empty database file will be created automatically upon running the application.
* Select an optional base path, the one which will be prepended to all paths in the database. Database paths are otherwise treated as absolute paths.
* Select an optional hexadecimal code of the default color for new tags. The default value is otherwise gray (RGB #d9d9d9).

Simply uncomment and enter the desired value(s).

After running the application, the Tagger app is accessible under `/pathtagger/` relative URL (e.g. `http://localhost:8000/pathtagger/`).

The application has 4 modules:
* Homepage
* Path tagging
* Tag management
* Mapping management

The use is pretty simple and straightforward. A mapping is a combination of a path and a list of tags. Mappings without tags are pointless and, although they may not be removed from the database right away, certain actions performed by the user will trigger a purge of all such mappings automatically.

## Am I licensed to use this software?

In short, yes. This software is licensed under the MIT License which can be found in a [separate file](LICENSE.md).

## How can I get in touch with the author?

You can e-mail me at *25157560+dsardelic@users.noreply.github.com* .