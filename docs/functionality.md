# Functionality

In this file the basic functionality of Raveberry is explained.

Raveberry can be accessed by typing 'http://raveberry/' into your browser's address bar. If this does not work, make sure the accessing device is in the same network as Raveberry and the protocol is specified. To avoid DNS issues you can also try entering 'http://raveberry.local/' or its IP, e.g. 'http://192.168.1.42/'.

At the top of the page three elements can be seen: The logo, the current hashtag and a burger menu.  
* The logo acts as a link to the mainpage. If enough people are active, it changes to a colorful version.
* The hashtag is a randomly selected one of all previously submitted hashtags. With the '+' icon next to it, users can submit a new one. Since anyone can do that, your server personalizes quickly. This hashtag is changed everytime the page is reloaded.
* The burger menu opens a dropdown menu.

In the dropdown menu you can see the number of currently active users, the number of total visitors and a sun and moon icon. With these two icons users can switch between the default dark mode and a bright mode of the page.

In the middle of the page users can search for music. Their search terms are used to find the first Youtube video matching the search string. If the search term matches previously played songs, they will be suggested below.

To the left of the input field is a dice icon. When pressing this button a randomly selected song is inserted in the input field. It is chosen from all songs ever requested.

Next to each song in the queue as well as below the current song are two icons. With these up and down arrows, songs can be voted up or down. When the current song is over, it will be continued with the one with the most votes. If a song reaches a vote count of minus three (by default), it will be removed.
