const { exec } = require('child_process');
const fsPromises = require('fs').promises;

var http = require("http"),
  url = require("url"),
  path = require("path"),
  fs = require("fs");
  multiparty = require('multiparty');
port = process.argv[2] || 8080;


async function getUpdatedImagePath() {
    const infoFile = '/home/orangepi/current.txt';
    let initialMtime = 0;

    // 1. Lấy thời gian cập nhật hiện tại của file
    try {
        const stats = await fsPromises.stat(infoFile);
        initialMtime = stats.mtimeMs;
    } catch (e) {
        // Nếu file chưa tồn tại ở lần chạy đầu, không sao cả
    }

    // 2. Gửi lệnh ép feh ghi ra file
    exec("bash /home/orangepi/keyZero.sh", (error) => {
        if (error) console.error(`Error executing keyZero: ${error.message}`);
    });

    // 3. Chờ file được cập nhật (Polling)
    const maxWaitTime = 8000; // Cho feh tối đa 8 giây để load các bức ảnh cực nặng
    const interval = 100;     // Cứ 100ms kiểm tra một lần
    let elapsed = 0;

    return new Promise((resolve, reject) => {
        const checkFile = setInterval(async () => {
            try {
                const stats = await fsPromises.stat(infoFile);
                
                // Nếu thời gian sửa đổi của file lớn hơn lúc đầu -> feh đã ghi xong!
                if (stats.mtimeMs > initialMtime) {
                    clearInterval(checkFile);
                    
                    // Delay nhẹ thêm 50ms để đảm bảo HĐH đã lưu hoàn tất dữ liệu vào ổ cứng,
                    // tránh tình trạng đọc trúng lúc file đang được ghi dở (file rỗng)
                    setTimeout(async () => {
                        try {
                            const data = await fsPromises.readFile(infoFile, 'utf8');
                            resolve(data.trim());
                        } catch (err) {
                            reject(err);
                        }
                    }, 50);
                    return;
                }
            } catch (e) {
                // Đang lỗi đọc file tạm thời, bỏ qua chờ vòng lặp sau
            }

            // Nếu đợi quá lâu (quá 8 giây) mà feh vẫn chưa ghi xong -> Báo lỗi
            elapsed += interval;
            if (elapsed >= maxWaitTime) {
                clearInterval(checkFile);
                reject(new Error("Timeout: feh mất quá nhiều thời gian để load ảnh nặng."));
            }
        }, interval);
    });
}

async function isTaskRunning(taskName) {
	return new Promise((resolve) => {
        setTimeout(() => {
			console.log(taskName);
            exec(`ps aux | grep ${taskName} | grep -v grep`, (error, stdout, stderr) => {
				if (error) {
				  resolve(false);
				}
				if (stderr) {
				  resolve(false);
				}
				console.log(stdout);
				// If stdout is not empty, it means the task is running
				if (stdout) {
				  resolve(true);
				} else {
				  resolve(false);
				}
			});
			
        }, 1); // Simulate a delay for demonstration
    });
}

function deleteFolderRecursive(folder) {
    if (fs.existsSync(folder)) {
        fs.readdirSync(folder).forEach((file) => {
            const curPath = path.join(folder, file);
            if (fs.lstatSync(curPath).isDirectory()) {
                // Recursively delete the subdirectory
                deleteFolderRecursive(curPath);
            } else {
                // Delete the file
                fs.unlinkSync(curPath);
            }
        });
        // Delete the main folder
        fs.rmdirSync(folder);
        console.log('Folder deleted successfully');
    } else {
        console.log('Folder does not exist');
    }
}

function onServerStart() {
    console.log('Server has started successfully!');
    const command = "bash /home/orangepi/runframe.sh &";

	exec(command, (error, stdout, stderr) => {
		if (error) {
			console.error(`Error: ${error.message}`);
		}
		if (stderr) {
			console.error(`stderr: ${stderr}`);
		}
		console.log(`stdout: ${stdout}`);
	});
}

function syncFileSystem()
{
	const command = "sudo sync";

	exec(command, (error, stdout, stderr) => {
		if (error) {
			console.error(`Error: ${error.message}`);;
		}
		if (stderr) {
			console.error(`stderr: ${stderr}`);
		}
		console.log(`stdout: ${stdout}`);
	});
}

http
  .createServer(async (request, response) => {
    var uri = url.parse(request.url).pathname,
      filename = path.join(process.cwd(), "docs", uri);
      
    // ----------------------------------------------------
    if (uri === "/stopFrame") {
        const command = "pkill -f 'runframe|feh'";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            // Gửi response 1 lần duy nhất
            response.writeHead(200, { "Content-Type": "text/plain" });
            response.end("STOPDONE");
        });
    }
    // ----------------------------------------------------
    else if (uri === "/runFrame") {
        let command = "bash /home/orangepi/runframe.sh &";
        const uploadDir = '/home/orangepi/upload';
        
        if (fs.existsSync(uploadDir)) {
            command = "bash /home/orangepi/runframeUpload.sh &";
        }

        // Kích hoạt bash script nhưng không chờ nó kết thúc
        exec(command, (error) => {
            if (error) console.error(`Error: ${error.message}`);
        });

        // Tách luồng trả kết quả ra ngoài độc lập.
        // Chờ 800ms để đảm bảo feh đã khởi động xong rồi mới báo trình duyệt
        setTimeout(() => {
            response.writeHead(200, { "Content-Type": "text/plain" });
            response.end("RUNDONE");
        }, 800);
    }
    // ----------------------------------------------------
    else if (uri === "/next") {
        const command = "bash /home/orangepi/keyRight.sh";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            setTimeout(() => {
                response.writeHead(200, { "Content-Type": "text/plain" });
                response.end("RIGHT");
            }, 500);
        });
    }
    // ----------------------------------------------------
    else if (uri === "/prev") {
        const command = "bash /home/orangepi/keyLeft.sh";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            setTimeout(() => {
                response.writeHead(200, { "Content-Type": "text/plain" });
                response.end("LEFT");
            }, 500);
        });
    }
    // ----------------------------------------------------
    else if (uri === "/currentImage") {
        if (await isTaskRunning('feh') == false) {
            response.writeHead(404, { 
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-store, no-cache, must-revalidate' 
            });
            response.end('Image not found');
            return;
        }
        
        try {
            // Thay thế 2 hàm cũ bằng hàm mới này
            const imagePath = await getUpdatedImagePath(); 
            
            fs.stat(imagePath, (err, stats) => {
                if (err || !stats.isFile()) {
                    response.writeHead(404, { 
                        'Content-Type': 'text/plain',
                        'Cache-Control': 'no-store, no-cache, must-revalidate'
                    });
                    response.end('Image not found');
                    return;
                }
                
                response.writeHead(200, { 
                    'Content-Type': 'image/jpeg',
                    'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                });
                fs.createReadStream(imagePath).pipe(response);
            });
        } catch (error) {
            console.error(error);
            response.writeHead(500, { 'Content-Type': 'text/plain' });
            response.end('Server error: ' + error.message);
        }
    }
    // ----------------------------------------------------
    else if (uri === "/upload" && request.method === 'POST') {
        const form = new multiparty.Form();
        form.parse(request, (err, fields, files) => {
            if (err) {
                response.writeHead(500, {'Content-Type': 'text/plain'});
                response.end('Error parsing form data');
                return;
            }

            const uploadedFile = files.file[0]; 
            const tempPath = uploadedFile.path;
            const uploadDir = '/home/orangepi/upload';
            
            if (fs.existsSync(uploadDir)) {
                deleteFolderRecursive(uploadDir);
            }
            if (!fs.existsSync(uploadDir)) {
                fs.mkdirSync(uploadDir);
            }

            const newPath = path.join(uploadDir, uploadedFile.originalFilename);
            
            fs.copyFile(tempPath, newPath, (err) => {
                if (err) {
                    response.writeHead(500, { 'Content-Type': 'text/plain' });
                    response.end('File upload failed');
                    return;
                }

                fs.unlink(tempPath, (err) => {
                    if (err) console.error("Error deleting temp file:", err);
                });
                
                const command1 = "pkill -f 'runframe|feh'";
                exec(command1, (error, stdout, stderr) => {
                    
                    const command2 = "bash /home/orangepi/runframeUpload.sh &";
                    // Khởi chạy ảnh upload nhưng không chờ feh tắt
                    exec(command2, (error) => {
                        if (error) console.error(`Error: ${error.message}`);
                    });

                    // Báo thành công luôn sau khi gọi lệnh
                    setTimeout(() => {
                        response.writeHead(200, { "Content-Type": "text/plain" });
                        response.end("UPLOAD DONE");
                    }, 800); 
                });
                syncFileSystem();
            });
        });
    }
    // ----------------------------------------------------
    else if (uri === "/delete") {
        const uploadDir = '/home/orangepi/upload'; 
        if (fs.existsSync(uploadDir)) {
            deleteFolderRecursive(uploadDir);
        }
        
        const command = "pkill -f 'runframe|feh'";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            response.writeHead(200, { "Content-Type": "text/plain" });
            response.end("DELETED");
        });
        syncFileSystem();
    }
    // ----------------------------------------------------
    else if (uri === "/OFFSCREEN") {
        const command = "bash /home/orangepi/turn-off-screen.sh";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            setTimeout(() => {
                response.writeHead(200, { "Content-Type": "text/plain" });
                response.end("OFFSCREEN");
            }, 500);
        });
    }
    // ----------------------------------------------------
    else if (uri === "/ONSCREEN") {
        const command = "bash /home/orangepi/turn-on-screen.sh";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            setTimeout(() => {
                response.writeHead(200, { "Content-Type": "text/plain" });
                response.end("ONSCREEN");
            }, 500);
        });
    }
    // ----------------------------------------------------
    else if (uri === "/REBOOT") {
        const command = "bash /home/orangepi/reboot.sh";
        exec(command, (error, stdout, stderr) => {
            if (error) console.error(`Error: ${error.message}`);
            else if (stderr) console.error(`stderr: ${stderr}`);
            else console.log(`stdout: ${stdout}`);

            setTimeout(() => {
                response.writeHead(200, { "Content-Type": "text/plain" });
                response.end("REBOOT");
            }, 500);
        });
    }
    // ----------------------------------------------------
    else if (uri === "/upload-light-novel-epub" && request.method === 'POST') {
        const form = new multiparty.Form();
        form.parse(request, (err, fields, files) => {
            if (err) {
                response.writeHead(500, {'Content-Type': 'text/plain'});
                response.end('Error parsing form data');
                return;
            }

            const folderName = (fields.folder_name && fields.folder_name[0]) ? fields.folder_name[0] : 'default_series';
            
            if (!files.file || !files.file[0]) {
                response.writeHead(400, {'Content-Type': 'text/plain'});
                response.end('No file uploaded');
                return;
            }
            
            const uploadedFile = files.file[0];
            const tempPath = uploadedFile.path;
            
            // Sanitize folderName: keep alphanumeric, space, dot, hyphen, underscore, and Vietnamese chars
            // The simplest way to sanitize against path traversal is replacing slashes, backslashes, etc.
            let safeFolderName = folderName.replace(/[<>:"/\\|?*\x00-\x1F]/g, '_').trim();
            if (!safeFolderName) safeFolderName = 'default_series';

            const baseDir = '/home/orangepi/mycloud/kavita/DATA/pixiv-light-novel';
            const targetDir = path.join(baseDir, safeFolderName);

            if (!fs.existsSync(baseDir)) {
                fs.mkdirSync(baseDir, { recursive: true });
            }
            if (!fs.existsSync(targetDir)) {
                fs.mkdirSync(targetDir, { recursive: true });
            }

            const newPath = path.join(targetDir, uploadedFile.originalFilename);
            
            fs.copyFile(tempPath, newPath, (err) => {
                if (err) {
                    response.writeHead(500, { 'Content-Type': 'text/plain' });
                    response.end('File upload failed: ' + err.message);
                    return;
                }

                fs.unlink(tempPath, (err) => {
                    if (err) console.error("Error deleting temp file:", err);
                });
                
                response.writeHead(200, { "Content-Type": "text/plain" });
                response.end("UPLOAD DONE");
            });
        });
    }
    // ----------------------------------------------------
    else {
        var extname = path.extname(filename);
        var contentType = "text/html";
        switch (extname) {
          case ".js": contentType = "text/javascript"; break;
          case ".css": contentType = "text/css"; break;
          case ".ico": contentType = "image/x-icon"; break;
          case ".svg": contentType = "image/svg+xml"; break;
        }

        fs.exists(filename, function(exists) {
          if (!exists) {
            response.writeHead(404, { "Content-Type": "text/plain" });
            response.write("404 Not Found\n");
            response.end();
            return;
          }

          if (fs.statSync(filename).isDirectory()) filename += "/index.html";

          fs.readFile(filename, "binary", function(err, file) {
            if (err) {
              response.writeHead(500, { "Content-Type": "text/plain" });
              response.write(err + "\n");
              response.end();
              return;
            }
            response.writeHead(200, { "Content-Type": contentType });
            response.write(file, "binary");
            response.end();
          });
        });
    }
  })
  .listen(parseInt(port, 10), () => {
    //onServerStart();
  });
console.log("WebUI Aria2 Server is running on http://localhost:" + port);
