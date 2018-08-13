# Tagger

## What is Tagger?

Tagger is a simple web application for assigning tags to file or folder paths, and searching tagged elements based on an arbitrary selection of tags.

## Why would I use it?

For instance, let's say you have a large collection of movies in one of your storages. All the movies are probably on a single location, perhaps distributed in several subfolders based on their _primary_ genre. One day your partner asks you to watch a movie together. He/she would like to watch a comedy, but, since he/she is easily scared, doesn't want a comedy with elements of horror. If you have many comedies and you haven't seen them all already, then you can't really be sure if your partner will be satisfied with your selection. If only there was a way to search for a set of movies with specific desired traits... Hello, Tagger!

## Is it something unique?

No, plenty of software can be found that does pretty much the same thing. However, some of the other solutions are not freeware, some don't enable tagging of files **and** folders, and some are way too complicated and have a plethora of features that are unnecessary for basic use. I used to use [Tabbles](https://tabbles.net), but it was just too big and just ran too slow. Recently I stumbled upon another [file-tagger](https://sourceforge.net/projects/file-tagger/) which I haven't tried out yet, but which seems to cover the same use cases.

## How does it work?

Tagger is a Python (3.5) web application created using the Django (2.0.6) framework. It uses a simple JSON document-oriented database written in Python called [TinyDB](http://tinydb.readthedocs.io) to store all tag and mapping data. The requirements can be found in a [separate file](requirements.txt).

## How do I use it?

Before running the application, it is required to edit the [Tagger.ini](Tagger.ini) file in order to:
* Name the absolute path to the JSON file to be used as a database
* Select the hexadecimal code of the default new tag color

The application has 4 modules:
* Homepage
* Path tagging
* Tag management
* Mapping management

The use is pretty simple and straightforward. A mapping is a combination of a path and a list of tags. Mappings without tags are pointless and, although they may not be removed right away, certain actions performed by the user will trigger a purge of all such mappings.

## Am I licensed to use this software?

This software is licensed under the MIT License which can be found in a [separate file](LICENSE.md).

## How can I get in touch with the author?

You can e-mail me at sardinhoATgmail.com.
