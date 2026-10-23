#include <stdio.h>

int main() {
	int score  = 20;
	int my_score;
	printf("hello my score :");
	scanf("%d" , &my_score);
	my_score += score;
	printf("New score %d:" , my_score);
	return 0;
}