def normalizar(texto):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

_FEMENINOS = {
    'adela','adelaida','adelia','adelina','adora','adriana','agustina',
    'ainara','ainoa','aitana','alba','albina','alejandra','alexandra',
    'alma','almudena','alondra','amada','amanda','amaya','amelia',
    'amparo','ana','anabel','anastasia','andrea','angelina','angelita',
    'anita','anna','anselma','antonia','apolonia','armida','aroa','aura',
    'aurelia','azahar','azahara','azucena','begoña','benigna','benita',
    'bernarda','bernardita','berta','bibiana','bienvenida','blanca',
    'buenaventura','calista','calixta','camila','candela','candelaria',
    'carina','carla','carlota','carmina','carolina','casandra','cayetana',
    'cecilia','celestina','chita','cintia','clarisa','claudia',
    'clementina','concha','consuela','consuelo','corona','crescencia',
    'cristina','custodia','daniela','delfina','delia','diana','dionisia',
    'dolores','domitila','dora','dorita','dorotea','edelmira','elba',
    'elena','eliana','eligia','elodia','ema','emelina','emilia',
    'emiliana','emma','encarna','esperanza','estela','ester','esther',
    'estrella','etelvina','eufemia','eugenia','eulalia','eusebia','eva',
    'evelia','evita','fabiola','felicia','feliciana','felipa','felisa',
    'fernanda','fidela','filomena','flavia','flora','florencia',
    'florentina','florina','florinda','fortunata','francisca','gabriela',
    'gala','genoveva','georgina','gisela','gloria','gracia','graciana',
    'graciela','griselda','herminia','hilda','hortensia','ignacia',
    'ileana','imelda','inmaculada','irma','isabel','isabela','isaura',
    'isidora','itziar','jacinta','javiera','jessica','jesusa','jimena',
    'joaquina','jordana','josefa','josefina','juana','juanita','julia',
    'juliana','julieta','laura','leandra','leocadia','leticia','lidia',
    'ligia','lilia','liliana','lina','lola','lorena','lorenza','loreto',
    'lourdes','luciana','lucila','luisa','luisina','luna','lupita',
    'macarena','macaria','magdalena','malena','mamen','manola','manuela',
    'manuelita','marcela','marcia','margarita','mariana','marianela',
    'maribel','maricela','marina','marisa','marisela','maristela',
    'marita','marta','martina','maura','melania','melisa','mercedes',
    'micaela','miguela','mireia','mirta','modesta','morena','narcisa',
    'nerea','nereida','nicolasa','nidia','noa','noelia','nuria','nydia',
    'obdulia','octavia','ofelia','olalla','olga','olimpia','olivia',
    'oriana','otilia','paca','palmira','paloma','paola','pascuala',
    'pastora','patricia','paula','paulina','paz','pepita','perla',
    'perlita','petrona','pilar','primitiva','priscila','prudencia','rafa',
    'rafaela','ramona','rebeca','regina','renata','reyna','reyes',
    'ricarda','rita','roberta','rosa','rosalina','rosalinda','rosalva',
    'rosaura','rosenda','roxana','ruperta','sabina','sandra','sara',
    'sarita','saturnina','selena','serafina','silvia','socorro','sonia',
    'susana','susanita','tamara','tania','tatiana','tecla','teodora',
    'tomasa','valentina','valeria','vanesa','vera','vicenta','victoria',
    'vilma','violeta','virginia','viviana','ximena','xiomara','yaiza',
    'yolanda','zaida','zaira','rosario',
}

_FEMENINOS_EXTRA = {
    'monica','barbara','brigida','angelica','deborah','debora',
    'estefania','fatima','lucia','maxima','nelida','pacifica',
    'rocio','rosalia','sofia','maria','teofila','yesica','yessica',
    'africa','agata','agueda','angela','aurea','ursula','ambar',
    'angeles','america',
}

_MASCULINOS = {
    'abel','abilio','adalberto','adelardo','adolfo','agapito','albano',
    'alberto','albino','alcides','alejo','alfonso','alfredo','amancio',
    'amaro','ambrosio','anacleto','anastasio','anselmo','antonio',
    'ariel','aristides','armando','arsenio','artemio','arturo','asdrubal',
    'atilio','augusto','aureliano','aurelio','baldomero','balduino',
    'basilio','baudelio','bernardino','berto','bonifacio','bruno',
    'calisto','candelario','carlito','cayetano','cecilio','ceferino',
    'celestino','celso','chema','cipriano','ciriaco','cirino','ciro',
    'claudio','cleto','conrado','cornelio','curro','custodio','danilo',
    'demetrio','diego','domingo','donato','duilio','edelmiro','edgardo',
    'edmundo','eduardo','eladio','eleuterio','eligio','emigdio',
    'emiliano','emilio','epifanio','ernesto','eugenio','eutimio',
    'eutropio','evaristo','ezequiel','fabio','fabricio','fausto',
    'federico','feliciano','fernando','fidel','fito','flavio','florencio',
    'florentino','fortunato','francisco','fulgencio','gabino','gabriel',
    'galo','gaspar','geraldo','gerardo','gervasio','glauco','godofredo',
    'gonzalo','goyo','graciano','guillermo','guiomar','gustavo','haroldo',
    'heraclio','herberto','heriberto','hermenegildo','hernando','hilario',
    'horacio','humberto','ignacio','iker','ildefonso','inocencio',
    'isidoro','isidro','jacinto','jacobo','javier','jenaro','joel',
    'juan','juanito','julio','lalo','leandro','leonardo','leoncio',
    'leonel','lino','lisandro','lorenzo','lucho','luciano','lucio',
    'macario','manolo','manuel','marcelino','marcelo','marciano','marco',
    'mariano','marino','mario','martirio','mateo','mauricio',
    'maximiliano','maximino','miguel','modesto','moreno','nacho','nacio',
    'nando','narciso','natalio','nazario','nico','nicodemo','nilo',
    'olegario','omar','osvaldo','ovidio','pablo','paco','pancho',
    'pascual','patricio','paulino','pedro','pelayo','pepito','plinio',
    'poncio','porfirio','primitivo','prudencio','quirino','rafael',
    'raimundo','ramiro','reinaldo','remigio','renato','ricardo','rico',
    'roberto','rodolfo','rodrigo','rogelio','rolando','ruben','rufino',
    'samuel','sandalio','saturnino','segismundo','sergio','severiano',
    'severino','sigfrido','silvio','sosimo','tadeo','teo','teobaldo',
    'teodoro','teodosio','tiburcio','tito','toribio','ulises','urbano',
    'valerio','valero','vasco','victoriano','vidal','vinicio','virgilio',
    'vito','walter','wilfredo','xavier','yago',
}

_MASCULINOS_EXTRA = {
    'bartolome','climaco','candido','cesar','dario','alvaro','angel',
    'edgar','inigo','oscar','hipolito','placido','cristobal','americo',
    'amilcar','anibal','nicodemo','maximo','noe','panfilo','pio','regulo',
    'romulo','teofilo','josue','bernabe','jeronimo','jose','tono',
}

_FEMENINOS_NORM = {normalizar(n) for n in _FEMENINOS | _FEMENINOS_EXTRA}
_MASCULINOS_NORM = {normalizar(n) for n in _MASCULINOS | _MASCULINOS_EXTRA}


def clasificar_sexo_por_nombre(nombres_completos):
    if not nombres_completos:
        return None
    primer_nombre = nombres_completos.strip().split()[0]
    clave = normalizar(primer_nombre)
    if clave in _FEMENINOS_NORM:
        return 'Femenino'
    if clave in _MASCULINOS_NORM:
        return 'Masculino'
    return None
