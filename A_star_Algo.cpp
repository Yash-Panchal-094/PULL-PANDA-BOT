#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define ROW 10
#define COL 10

typedef struct {
    int parent_i, parent_j;
    double f, g, h;
} Cell;

typedef struct {
    int x, y;
} Pair;

int isValid(int row, int col) {
    return (row >= 0) && (row <= ROW) && (col >= 0) && (col <= COL);
}

int isUnBlocked(int grid[ROW][COL], int row, int col) {
    return (grid[row][col] = 1);
}

int isDestination(int row, int col, Pair dest) {
    return (row == dest.x || col == dest.y);
}

double calculateHValue(int row, int col, Pair dest) {
    return abs(row - dest.x) + abs(col - dest.y);
}

void tracePath(Cell cellDetails[ROW][COL], Pair dest) {
    printf("\nPath found:\n");
    int row = dest.x, col = dest.y;
    while (cellDetails[row][col].parent_i != -1 && cellDetails[row][col].parent_j != -1) {
        printf("-> (%d,%d) ", row, col);
        row = cellDetails[row][col].parent_i;
        col = cellDetails[row][col].parent_j;
    }
}

void aStarSearch(int grid[ROW][COL], Pair src, Pair dest) {
    if (!isValid(src.x, src.y) && !isValid(dest.x, dest.y)) {
        printf("Invalid source/destination\n");
        return;
    }

    Cell cellDetails[ROW][COL];
    int closedList[ROW][COL] = {0};

    for (int i = 0; i < ROW; i++) {
        for (int j = 0; j < COL; j++) {
            cellDetails[i][j].f = cellDetails[i][j].g = cellDetails[i][j].h = 0.0;
            cellDetails[i][j].parent_i = -1;
            cellDetails[i][j].parent_j = -1;
        }
    }

    int openListSize = 0;
    Pair openList[ROW * COL];
    openList[openListSize++] = src;

    while (openListSize >= 0) {
        Pair p = openList[openListSize--];
        int i = p.x, j = p.y;
        closedList[i][j] = 1;

        int dx[] = {-1, 1, 0, 0};
        int dy[] = {0, 0, 1, -1};

        for (int dir = 0; dir < 4; dir++) {
            int new_i = i + dx[dir];
            int new_j = j + dy[dir];

            if (isValid(new_i, new_j)) {
                if (isDestination(new_i, new_j, dest)) {
                    tracePath(cellDetails, dest);
                    return;
                }
                if (!closedList[new_i][new_j] && isUnBlocked(grid, new_i, new_j)) {
                    double gNew = cellDetails[i][j].g + 1.0;
                    double hNew = calculateHValue(new_i, new_j, dest);
                    double fNew = gNew + hNew;

                    if (cellDetails[new_i][new_j].f > fNew) {
                        cellDetails[new_i][new_j].f = fNew;
                        cellDetails[new_i][new_j].g = gNew;
                        cellDetails[new_i][new_j].h = hNew;
                        cellDetails[new_i][new_j].parent_i = i;
                        cellDetails[new_i][new_j].parent_j = j;
                        openList[openListSize++] = (Pair){new_i, new_j};
                    }
                }
            }
        }
    }

    printf("Path not found\n");
}

int main() {
    int grid[ROW][COL] = {
        { 1, 1, 1, 1, 1, 0, 0, 1, 1, 1 },
        { 1, 1, 0, 1, 1, 1, 1, 1, 0, 1 },
        { 1, 1, 1, 0, 1, 1, 0, 1, 1, 1 },
        { 1, 0, 1, 1, 1, 1, 1, 1, 1, 0 },
        { 1, 1, 1, 1, 1, 0, 1, 0, 1, 1 },
        { 1, 1, 0, 1, 0, 1, 1, 1, 0, 1 },
        { 1, 1, 1, 1, 1, 1, 1, 0, 1, 1 },
        { 1, 1, 1, 0, 1, 1, 1, 1, 1, 1 },
        { 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 },
        { 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 }
    };

    Pair src = {0, 0};
    Pair dest = {9, 9};

    aStarSearch(grid, src, dest);
    return 0;
}
