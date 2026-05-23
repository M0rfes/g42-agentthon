CLI TODO manager

its a cli that is used to manage todo and fix commens in a code base. when the cli is invoced it read all the fiels from all subdirs and looks for TODO/todo fix/FIX comments
list them with filenames line number and comment messge
the commnet can have optionl tags the syntex for tag [key=value]
eg: //TODO: take over the wokrd [priority=low] [due=12-06-2026]
then the cli can be used to filter the TODOS like todo priority=heigh
implement logial opperators like eq not eq includes no includes lt gt lte gte between
number will alwys be int and date be of formate DD-MM-YYYY. any thing that not a interger or date is a string
