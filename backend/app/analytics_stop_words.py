"""Common Russian and English function words excluded from keyword rankings."""

RUSSIAN_STOP_WORDS = frozenset(
    """
    а без более бы был была были было быть в вам вами вас весь во вот все
    всего всех вы где да даже для до его ее её если есть еще ещё же за и из
    или им ими их к как какая какие каким какими каких какой ко когда кого
    кому которая которые который которым которыми которых которую которого
    которой которое кто куда ли либо мне много может можно мой моя мои моё
    мною мной мы на над надо наш наша наши наше нашего нашей нашим нашими
    наших не него нее неё ней нем нему нет нету ни них ничего но ну о об
    один одна одни одно одного одной одном одному одними одних он она они
    оно от потому после по при про пусть пускай с сам сама сами само своего
    своей своим своими своих себе себя сегодня сейчас со такой такая такие
    такое такого такой таким такими таких там те тем тех то того той только
    том тому тот та те три тут ты у уже хотя чего чей чья чьё чьи чем через
    что чтобы чём эта эти это этого этой этом этому эту я
    ведь впрочем вообще дескать именно итак именно как-либо мол неужели
    однако откуда отсюда разве равно будто словно пусть пускай уж хоть лишь
    исключительно именно просто прямо едва чуть почти будто бы
    """.split()
)

ENGLISH_STOP_WORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because
    been before being below between both but by can cannot could did do does
    doing down during each few for from further had has have having he her
    here hers herself him himself his how i if in into is it its itself just
    me more most my myself no nor not of off on once only or other ought our
    ours ourselves out over own same she should so some such than that the
    their theirs them themselves then there these they this those through to
    too under until up very was we were what when where which while who whom
    why with would you your yours yourself yourselves
    after all although always among amongst another anywhere anyhow anyone
    anything anyway anyways around back became become becomes becoming beside
    besides beyond bill call co computer con couldnt cry de describe detail
    done due eg eight either eleven else elsewhere empty enough etc even ever
    every everyone everything everywhere except few fifteen fifty fill find
    fire first five former formerly forty found four front full get give go
    hadnt hasnt havent hence herein hereby herein hereupon however hundred ie
    inc indeed interest instead keep last latter latterly least less ltd many
    may meanwhile mill mine moreover mostly move much must name neither never
    nevertheless next nine ninety nobody none noone nothing nowhere now
    nowhere often other others otherwise our ours outside part per perhaps
    please put rather re same see seem seemed seeming seems serious several
    seventeen seventy six sixty somehow someone something sometime sometimes
    somewhere still thence thereafter thereby therefore therein thereof
    thereupon thirty three throughout thru thus top toward towards twelve
    twenty two un under unless unlike unlikely upon used using various via
    well whatever whenever wherever whether whoever whole whose within without
    wont
    ain't aren't couldn't didn't doesn't don't hadn't hasn't haven't isn't
    mightn't mustn't needn't shouldn't wasn't weren't wouldn't
    """.split()
)

STOP_WORDS = RUSSIAN_STOP_WORDS | ENGLISH_STOP_WORDS
