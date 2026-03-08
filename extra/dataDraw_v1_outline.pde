
 Table table;
 int i=0;
 
void setup(){ 
   table = loadTable("cityComp.csv", "header");
   size(1000,1000);
  //background(145,151,174);
  background(229,236,233);

 }
 void draw(){

       if((i<table.getRowCount())&&(mousePressed)){
        TableRow row = table.getRow(i);
        
        //won't load anything bigger than 999...
        int size =row.getInt("TOTAL");
        String type = row.getString("DEPARTMENT_NAME");
        int edu = row.getInt("Education");
        
        
        //int test = size;
       // println(type);
        if(type.equals("Boston Police Department")){
          stroke(249,0,147,50);
          println(true);
        }else if(type.equals("Boston Fire Department")){
          //fill(19,60,85,100);
          stroke(249,0,147,50);
        }else if(edu == 1){
          stroke(246,174,45,50);
        }else{stroke(124,127,101,25);
        println(false);
        }
        

        noFill();
        ellipse(mouseX,mouseY,(20*(sqrt(size/PI))),(20*(sqrt(size/PI))));
        //ellipse(mouseX,mouseY,(size/10000),(size/10000));
        //ellipse(mouseX,mouseY,size,size);

        i=i+1;
        
        }

 }
